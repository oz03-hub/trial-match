"""Deterministic markdown report built from the final lists (no LLM involved).

Only the fixed labels and the disclaimer are translated. Trial titles, quotes
and contacts come straight from the data, and the agent-written fields
(why, criterion text, question) are already in the user's language.

Each trial ends with a draft outreach email (always English: coordinators read
English) in a blockquote. The body comes from a report-time LLM call (see
outreach.py) passed in as `emails`; code adds the greeting, subject, sign-off
and footer, and builds a deterministic body if the LLM's is missing.
"""

import re

from app.schemas import Hospital, Trial, TrialMatchResponse

# {url} is the trial's ClinicalTrials.gov page.
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Your TrialMatch report",
        "empty": "We didn't find recruiting Massachusetts trials that match what you shared.",
        "fit": "Looks like a fit",
        "closer": "Worth a closer look",
        "why": "Why it's relevant:",
        "checklist": "Eligibility checklist:",
        "met": "Met",
        "unmet": "Not met",
        "unknown": "Unknown",
        "ask": "Ask the study coordinator:",
        "sites": "Recruiting sites:",
        "no_sites": "No recruiting sites listed; contact the team via the [study page]({url}).",
        "contact_via": "contact via the [study page]({url})",
        "email": "Draft message to the study team (in English; add your name and edit before sending):",
        "rating": "CMS rating",
        "disclaimer": (
            "_This report is not medical advice. Only the study team can decide whether you are "
            "eligible for a trial. Bring these questions to the study coordinator, and talk with "
            "your own doctor before joining any study._"
        ),
    },
    "es": {
        "title": "Su informe de TrialMatch",
        "empty": "No encontramos ensayos clínicos en Massachusetts que estén reclutando y coincidan con lo que nos contó.",
        "fit": "Parece una buena opción",
        "closer": "Vale la pena revisar",
        "why": "Por qué es relevante:",
        "checklist": "Lista de requisitos de elegibilidad:",
        "met": "Cumple",
        "unmet": "No cumple",
        "unknown": "Se desconoce",
        "ask": "Pregunte al coordinador del estudio:",
        "sites": "Centros que están reclutando:",
        "no_sites": "No hay centros de reclutamiento en la lista; comuníquese con el equipo a través de la [página del estudio]({url}).",
        "contact_via": "comuníquese a través de la [página del estudio]({url})",
        "email": "Borrador de mensaje para el equipo del estudio (en inglés; agregue su nombre y edítelo antes de enviarlo):",
        "rating": "Calificación de CMS",
        "disclaimer": (
            "_Este informe no es consejo médico. Solo el equipo del estudio puede decidir si usted es "
            "elegible para un ensayo. Lleve estas preguntas al coordinador del estudio y hable con su "
            "propio médico antes de participar en cualquier estudio._"
        ),
    },
    "pt": {
        "title": "Seu relatório do TrialMatch",
        "empty": "Não encontramos ensaios clínicos em Massachusetts que estejam recrutando e correspondam ao que você informou.",
        "fit": "Parece uma boa opção",
        "closer": "Vale a pena analisar",
        "why": "Por que é relevante:",
        "checklist": "Lista de critérios de elegibilidade:",
        "met": "Atende",
        "unmet": "Não atende",
        "unknown": "Desconhecido",
        "ask": "Pergunte ao coordenador do estudo:",
        "sites": "Locais que estão recrutando:",
        "no_sites": "Nenhum local de recrutamento listado; entre em contato com a equipe pela [página do estudo]({url}).",
        "contact_via": "entre em contato pela [página do estudo]({url})",
        "email": "Rascunho de mensagem para a equipe do estudo (em inglês; adicione seu nome e edite antes de enviar):",
        "rating": "Avaliação do CMS",
        "disclaimer": (
            "_Este relatório não é aconselhamento médico. Somente a equipe do estudo pode decidir se "
            "você é elegível para um ensaio. Leve estas perguntas ao coordenador do estudo e converse "
            "com seu próprio médico antes de participar de qualquer estudo._"
        ),
    },
    "zh": {
        "title": "您的 TrialMatch 报告",
        "empty": "我们没有找到与您所提供信息相符、且正在招募的马萨诸塞州临床试验。",
        "fit": "看起来合适",
        "closer": "值得进一步了解",
        "why": "相关原因：",
        "checklist": "入选条件核对表：",
        "met": "符合",
        "unmet": "不符合",
        "unknown": "未知",
        "ask": "请询问研究协调员：",
        "sites": "正在招募的研究地点：",
        "no_sites": "未列出正在招募的研究地点；请通过[研究页面]({url})联系研究团队。",
        "contact_via": "请通过[研究页面]({url})联系",
        "email": "给研究团队的消息草稿（英文；发送前请填写姓名并修改）：",
        "rating": "CMS 评级",
        "disclaimer": (
            "_本报告不构成医疗建议。只有研究团队才能决定您是否符合试验条件。"
            "请向研究协调员咨询这些问题，并在参加任何研究之前咨询您自己的医生。_"
        ),
    },
    "ht": {
        "title": "Rapò TrialMatch ou",
        "empty": "Nou pa jwenn okenn esè klinik nan Massachusetts k ap rekrite ki koresponn ak sa ou te pataje a.",
        "fit": "Sanble li adapte ou",
        "closer": "Merite pou gade pi pre",
        "why": "Poukisa li enpòtan:",
        "checklist": "Lis kritè elijibilite:",
        "met": "Satisfè",
        "unmet": "Pa satisfè",
        "unknown": "Pa konnen",
        "ask": "Mande kowòdonatè etid la:",
        "sites": "Sit k ap rekrite:",
        "no_sites": "Pa gen okenn sit k ap rekrite ki nan lis la; kontakte ekip la atravè [paj etid la]({url}).",
        "contact_via": "kontakte atravè [paj etid la]({url})",
        "email": "Bouyon mesaj pou ekip etid la (an anglè; ajoute non ou epi modifye l anvan ou voye l):",
        "rating": "Evalyasyon CMS",
        "disclaimer": (
            "_Rapò sa a pa konsèy medikal. Se sèlman ekip etid la ki ka deside si ou elijib pou yon esè. "
            "Pote kesyon sa yo bay kowòdonatè etid la, epi pale ak pwòp doktè ou anvan ou antre nan "
            "nenpòt etid._"
        ),
    },
    "vi": {
        "title": "Báo cáo TrialMatch của bạn",
        "empty": "Chúng tôi không tìm thấy thử nghiệm lâm sàng nào đang tuyển ở Massachusetts phù hợp với những gì bạn đã chia sẻ.",
        "fit": "Có vẻ phù hợp",
        "closer": "Đáng xem xét kỹ hơn",
        "why": "Vì sao liên quan:",
        "checklist": "Danh sách tiêu chí đủ điều kiện:",
        "met": "Đạt",
        "unmet": "Không đạt",
        "unknown": "Chưa rõ",
        "ask": "Hỏi điều phối viên nghiên cứu:",
        "sites": "Các địa điểm đang tuyển:",
        "no_sites": "Chưa có địa điểm tuyển nào được liệt kê; hãy liên hệ nhóm nghiên cứu qua [trang nghiên cứu]({url}).",
        "contact_via": "liên hệ qua [trang nghiên cứu]({url})",
        "email": "Bản nháp tin nhắn gửi nhóm nghiên cứu (bằng tiếng Anh; thêm tên của bạn và chỉnh sửa trước khi gửi):",
        "rating": "Xếp hạng CMS",
        "disclaimer": (
            "_Báo cáo này không phải là lời khuyên y tế. Chỉ nhóm nghiên cứu mới có thể quyết định bạn "
            "có đủ điều kiện tham gia thử nghiệm hay không. Hãy mang những câu hỏi này đến điều phối "
            "viên nghiên cứu và trao đổi với bác sĩ của bạn trước khi tham gia bất kỳ nghiên cứu nào._"
        ),
    },
}

DISCLAIMER = LABELS["en"]["disclaimer"]

STATUS_MARK = {"met": "✅", "unmet": "❌", "unknown": "❓"}


def stars(rating: int) -> str:
    """4 -> ★★★★☆"""
    return "★" * rating + "☆" * (5 - rating)


def _rating_line(hospital: Hospital | None, label: str) -> str | None:
    if hospital is None or hospital.overall_rating is None:
        return None
    return f"  - {label} {stars(hospital.overall_rating)} ({hospital.overall_rating}/5)"


EMAIL_FOOTER = (
    "Matched with TrialMatch.org — pre-screened against the published eligibility criteria; "
    "final eligibility is up to the study team."
)
GREETING = "Dear Study Team,"


def fallback_body(trial: Trial, language: str = "en") -> str:
    """Deterministic English message: met criteria as facts, the rest as questions."""
    def crit(c, with_text: bool) -> str:
        # Criterion text is in the user's language; the quote is always English.
        if language != "en":
            return c.quote or c.text
        return f'{c.text} (study criterion: "{c.quote}")' if with_text and c.quote else c.text

    met = [c for c in trial.criteria if c.status == "met"]
    open_ = [c for c in trial.criteria if c.status != "met"]
    parts = [f'I am interested in the study "{trial.title}" ({trial.nct_id}).']
    if met:
        parts.append(
            "Based on what I shared, these study criteria look met for me:\n"
            + "\n".join(f"- {crit(c, True)}" for c in met)
        )
    if open_:
        parts.append(
            "I have questions about these criteria:\n"
            + "\n".join(f"- Could you tell me what is needed to check: {crit(c, False)}?" for c in open_)
        )
    else:
        parts.append("Could you tell me about the next steps to find out if I may be eligible?")
    return "\n\n".join(parts)


def _clean_body(body: str) -> str:
    """Drop any greeting/subject the model added; code supplies those."""
    lines = body.replace("\r", "").strip().splitlines()
    while lines and (not lines[0].strip() or re.match(r"\s*(subject:|dear\b)", lines[0], re.I)):
        lines.pop(0)
    # A paragraph right after a "- " item would render as part of that item.
    out: list[str] = []
    for line in lines:
        bullet = bool(re.match(r"\s*[-*•]\s", line))
        if out and out[-1].strip() and line.strip() and bullet != bool(re.match(r"\s*[-*•]\s", out[-1])):
            out.append("")
        out.append(line)
    return "\n".join(out).strip()


def email_block(trial: Trial, body: str | None, language: str = "en") -> list[str]:
    """The outreach email as markdown blockquote lines (no raw HTML)."""
    body = _clean_body(body or "") or fallback_body(trial, language)
    inner = [
        f'**Subject:** Interest in "{trial.title}" ({trial.nct_id})',
        "",
        GREETING,
        "",
        body,
        "",
        "Thank you,  ",
        "[Your name]  ",
        "[Phone or email]",
        "",
        EMAIL_FOOTER,
    ]
    # Keep the trailing double-space (hard line break) on the sign-off lines.
    return [f"> {line}" if line else ">" for line in "\n".join(inner).split("\n")]


def _trial_section(
    trial: Trial, t: dict[str, str], email_body: str | None = None, language: str = "en"
) -> list[str]:
    lines = [
        f"### {trial.title}",
        "",
        f"**[{trial.nct_id}]({trial.url})** · {trial.phase}",
        "",
        f"**{t['why']}** {trial.why}",
        "",
    ]
    if trial.criteria:
        lines += [f"**{t['checklist']}**", ""]
        for c in trial.criteria:
            lines.append(f"- {STATUS_MARK[c.status]} {t[c.status]}: {c.text}")
            if c.quote:
                lines.append(f"  - _\"{c.quote}\"_")
        lines.append("")
    if trial.question:
        lines += [f"**{t['ask']}** {trial.question}", ""]

    lines += [f"**{t['sites']}**", ""]
    if not trial.sites:
        lines.append("- " + t["no_sites"].format(url=trial.url))
    for s in trial.sites:
        contact = s.contact or t["contact_via"].format(url=trial.url)
        place = f"{s.city} {s.zip}".strip()
        lines.append(f"- {s.facility}, {place}: {contact}")
        if rating := _rating_line(s.hospital, t["rating"]):
            lines.append(rating)
    lines += ["", f"**{t['email']}**", "", *email_block(trial, email_body, language), ""]
    return lines


def build_report(
    response: TrialMatchResponse, language: str = "en", emails: dict[str, str] | None = None
) -> str:
    """`emails` maps nct_id -> LLM-written message body; missing ones use the fallback."""
    emails = emails or {}
    t = LABELS.get(language, LABELS["en"])
    lines = [f"# {t['title']}", ""]
    groups = [
        (t["fit"], response.looks_like_a_fit),
        (t["closer"], response.worth_a_closer_look),
    ]
    if not any(trials for _, trials in groups):
        lines += [t["empty"], ""]
    first = True
    for heading, trials in groups:
        if trials:
            if not first:
                lines += ["---", ""]
            first = False
            lines += [f"## {heading} ({len(trials)})", ""]
            for i, trial in enumerate(trials):
                if i > 0:
                    lines += ["---", ""]
                lines += _trial_section(trial, t, emails.get(trial.nct_id), language)
    lines += ["---", "", t["disclaimer"], ""]
    return "\n".join(lines)
