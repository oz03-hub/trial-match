"""Lay-term -> medical-term expansion for trial search.

Each query term (or multi-word lay phrase) becomes one "slot": the original
term plus its synonyms, joined with `|` so any of them may match. Slots are
still ANDed by the search. Alternatives are lowercase substrings, except those
of 3 characters or fewer, which the search matches on word boundaries (so "mi"
doesn't hit "migraine"). Avoid 4+ character alternatives that sit inside other
words ("stemi" is in "systemic", "renal" in "adrenal").
"""

import re

# (lay keys, alternatives). Keys are matched after lowercasing and dropping 's.
GROUPS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    # heart and circulation
    (("heart attack",), ("myocardial infarction", "mi", "acute coronary syndrome")),
    (("high blood pressure", "hypertension", "high bp"), ("hypertension", "hypertensive")),
    (("low blood pressure",), ("hypotension",)),
    (("heart failure", "congestive heart failure", "chf"), ("heart failure", "cardiac failure", "chf", "hfref", "hfpef")),
    (("heart disease", "heart problems"), ("heart disease", "coronary artery disease", "cad", "cardiovascular", "ischemic heart")),
    (("irregular heartbeat", "afib", "atrial fibrillation"), ("atrial fibrillation", "afib", "arrhythmia")),
    (("high cholesterol", "cholesterol"), ("cholesterol", "hypercholesterolemia", "hyperlipidemia", "dyslipidemia", "ldl")),
    (("stroke",), ("stroke", "cerebrovascular", "cerebral infarction", "cva")),
    (("mini stroke",), ("transient ischemic attack", "tia", "stroke")),
    (("blood clot", "clot"), ("blood clot", "thrombosis", "thromboembolism", "embolism", "dvt")),
    (("anemia",), ("anemia", "anaemia")),
    # metabolic, kidney, liver
    (("diabetes", "sugar", "sugar diabetes", "high blood sugar"), ("diabetes", "diabetic", "t2d", "t1d", "t2dm", "t1dm")),
    (("obesity", "overweight"), ("obes", "overweight")),
    (("kidney disease", "kidney failure"), ("kidney disease", "chronic kidney", "ckd", "renal failure", "renal impairment", "nephropathy")),
    (("kidney stone",), ("kidney stone", "nephrolithiasis", "urolithiasis")),
    (("fatty liver",), ("fatty liver", "nafld", "masld", "steatotic", "steatohepatitis")),
    # cancer
    (("cancer",), ("cancer", "carcinoma", "tumor", "tumour", "neoplasm", "malignan")),
    (("tumor", "tumour"), ("tumor", "tumour", "neoplasm", "cancer")),
    (("blood cancer",), ("leukemia", "lymphoma", "myeloma", "hematologic", "blood cancer")),
    (("skin cancer",), ("skin cancer", "melanoma", "basal cell", "squamous cell")),
    (("brain tumor", "brain cancer"), ("brain tumor", "brain cancer", "glioma", "glioblastoma", "brain neoplasm")),
    # brain and mental health
    (("alzheimer", "alzheimers", "dementia", "memory loss"), ("alzheimer", "dementia", "cognitive impairment")),
    (("parkinson", "parkinsons"), ("parkinson",)),
    (("depression", "depressed"), ("depress", "mdd", "major depressive")),
    (("anxiety", "anxious"), ("anxiety", "anxious", "gad", "panic disorder")),
    (("bipolar",), ("bipolar", "manic")),
    (("schizophrenia", "psychosis"), ("schizophrenia", "psychosis", "psychotic")),
    (("ptsd", "post traumatic stress"), ("ptsd", "post-traumatic", "posttraumatic", "post traumatic stress")),
    (("adhd", "attention deficit"), ("adhd", "attention deficit", "attention-deficit")),
    (("autism",), ("autism", "autistic", "asd")),
    (("epilepsy", "seizure"), ("epilepsy", "epileptic", "seizure")),
    (("multiple sclerosis", "ms"), ("multiple sclerosis", "ms")),
    (("als", "lou gehrig disease"), ("amyotrophic lateral sclerosis", "als", "motor neuron")),
    (("headache", "migraine"), ("migraine", "headache")),
    (("insomnia", "trouble sleeping"), ("insomnia", "sleep disturbance", "sleep disorder")),
    (("sleep apnea", "apnea"), ("sleep apnea", "osa", "obstructive sleep")),
    # lungs, infections
    (("asthma",), ("asthma", "bronchial")),
    (("copd", "emphysema", "chronic bronchitis"), ("copd", "chronic obstructive", "emphysema", "chronic bronchitis")),
    (("hiv", "aids"), ("hiv", "human immunodeficiency")),
    (("covid", "covid-19", "coronavirus"), ("covid", "sars-cov-2", "coronavirus")),
    (("flu", "influenza"), ("influenza", "flu")),
    (("shingles",), ("shingles", "herpes zoster", "zoster")),
    (("urinary tract infection", "uti", "bladder infection"), ("urinary tract infection", "uti", "cystitis")),
    # bones, joints, pain
    (("arthritis", "joint pain"), ("arthritis", "osteoarthritis", "rheumatoid", "joint pain")),
    (("osteoporosis", "brittle bones", "weak bones"), ("osteoporosis", "osteopenia", "bone density")),
    (("back pain",), ("back pain", "lumbar", "dorsalgia")),
    (("chronic pain",), ("chronic pain", "persistent pain")),
    (("broken bone",), ("fracture", "broken bone")),
    # gut, skin, eyes, ears
    (("crohn", "crohns", "colitis", "ibd"), ("crohn", "ulcerative colitis", "inflammatory bowel", "ibd")),
    (("ibs", "irritable bowel"), ("irritable bowel", "ibs")),
    (("acid reflux", "heartburn"), ("gerd", "reflux", "heartburn", "gastroesophageal")),
    (("celiac",), ("celiac", "coeliac", "gluten")),
    (("eczema",), ("eczema", "atopic dermatitis")),
    (("macular degeneration", "amd"), ("macular degeneration", "amd")),
    (("dry eye",), ("dry eye", "keratoconjunctivitis sicca")),
    (("hearing loss", "deafness"), ("hearing loss", "deafness", "hearing impairment", "sensorineural")),
    # reproductive, urinary, substance use
    (("menopause", "hot flashes"), ("menopause", "hot flash", "vasomotor")),
    (("pregnant", "pregnancy"), ("pregnan", "gestation")),
    (("enlarged prostate",), ("bph", "benign prostatic hyperplasia", "prostatic hyperplasia")),
    (("smoking", "smoker", "quit smoking", "tobacco"), ("smok", "tobacco", "nicotine")),
    (("alcoholism", "alcohol addiction", "drinking problem"), ("alcohol use disorder", "alcohol dependence", "alcoholism")),
    (("addiction", "drug addiction", "substance abuse", "opioid addiction"), ("addiction", "opioid use disorder", "substance use disorder")),
]


def _canon(word: str) -> str:
    """Lowercase, drop edge punctuation and a possessive 's ("Alzheimer's?" -> "alzheimer")."""
    word = word.lower().strip(".,;:!?()\"")
    return re.sub(r"['’]s$", "", word)


SYNONYMS: dict[str, tuple[str, ...]] = {
    " ".join(_canon(w) for w in key.split()): alts for keys, alts in GROUPS for key in keys
}
MAX_PHRASE_WORDS = max(len(key.split()) for key in SYNONYMS)


def _lookup(words: list[str]) -> tuple[str, ...] | None:
    """Alternatives for a lay phrase; the last word may be a plural ("heart attacks")."""
    key = " ".join(_canon(w) for w in words)
    if key in SYNONYMS:
        return SYNONYMS[key]
    if key.endswith("s") and key[:-1] in SYNONYMS:
        return SYNONYMS[key[:-1]]
    return None


def _expand_word(word: str) -> list[str]:
    """One query word: itself plus synonyms. Each side of a user-written `a|b` is expanded."""
    alts = [a for a in word.split("|") if a]
    return [*alts, *(syn for alt in alts for syn in _lookup([alt]) or ())]


def expand_query(query: str) -> list[str]:
    """Query -> search slots, e.g. "heart attack diabetes" ->
    ["heart attack|myocardial infarction|mi|...", "diabetes|diabetic|t2d|..."]."""
    words = query.lower().split()
    slots, i = [], 0
    while i < len(words):
        # longest lay phrase starting here wins, so "heart attack" beats "heart"
        n, found = 1, None
        for size in range(min(MAX_PHRASE_WORDS, len(words) - i), 1, -1):
            chunk = words[i:i + size]
            found = "|" not in "".join(chunk) and _lookup(chunk)
            if found:
                n = size
                break
        slot = [" ".join(words[i:i + n]), *found] if found else _expand_word(words[i])
        slots.append("|".join(dict.fromkeys(slot)))
        i += n
    return slots
