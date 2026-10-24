import type { Language } from "./types";

export const LANGUAGES: { code: Language; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português" },
  { code: "zh", label: "中文" },
  { code: "ht", label: "Kreyòl ayisyen" },
  { code: "vi", label: "Tiếng Việt" },
];

/** Only a few static strings are translated; everything else in the UI stays English. */
export interface Strings {
  intro: string;
  placeholder: string;
  allDone: string;
  fit: string;
  closer: string;
  /** Rotating status phrases shown while the agent is working. */
  searching: string[];
}

export const STRINGS: Record<Language, Strings> = {
  en: {
    intro:
      "Hi! I can help you find clinical trials that are recruiting in Massachusetts. " +
      "Tell me a bit about yourself in plain language — for example your age, your condition, and the town you live in. " +
      "I'll search the trials, show what looks like a fit, and ask one question at a time to narrow things down. " +
      "Nothing you type is stored on our server. This is not medical advice — a study coordinator always makes the final call." +
      "You can click \"All done — show my report\" any time you are satisfied with the matches to get a receipt of your list of eligible studies.",
    placeholder: "Type your answer or describe yourself…",
    allDone: "All done — show my report",
    fit: "Looks like a fit",
    closer: "Worth a closer look",
    searching: [
      "Searching trials…",
      "Expanding plain-language terms…",
      "Reading eligibility criteria…",
      "Checking recruiting sites…",
      "Narrowing the shortlist…",
    ],
  },
  es: {
    intro:
      "¡Hola! Puedo ayudarle a encontrar ensayos clínicos que están reclutando en Massachusetts. " +
      "Cuénteme un poco sobre usted con palabras sencillas: por ejemplo su edad, su afección y la ciudad donde vive. " +
      "Buscaré los ensayos, le mostraré los que parecen adecuados y le haré una pregunta a la vez. " +
      "Nada de lo que escriba se guarda en nuestro servidor. Esto no es consejo médico: el coordinador del estudio siempre toma la decisión final." +
      " Puede hacer clic en \"Listo — mostrar mi informe\" en cualquier momento, cuando esté satisfecho con las coincidencias, para obtener un recibo con su lista de estudios elegibles.",
    placeholder: "Escriba su respuesta o descríbase…",
    allDone: "Listo — mostrar mi informe",
    fit: "Parece adecuado",
    closer: "Vale la pena revisar",
    searching: [
      "Buscando ensayos…",
      "Ampliando términos sencillos…",
      "Leyendo los criterios de elegibilidad…",
      "Revisando los centros que reclutan…",
      "Afinando la lista…",
    ],
  },
  pt: {
    intro:
      "Olá! Posso ajudar você a encontrar ensaios clínicos que estão recrutando em Massachusetts. " +
      "Conte um pouco sobre você em palavras simples: por exemplo sua idade, sua condição e a cidade onde mora. " +
      "Vou pesquisar os ensaios, mostrar os que parecem adequados e fazer uma pergunta de cada vez. " +
      "Nada do que você digitar é armazenado no nosso servidor. Isto não é aconselhamento médico: o coordenador do estudo sempre toma a decisão final." +
      " Você pode clicar em \"Pronto — mostrar meu relatório\" a qualquer momento, quando estiver satisfeito com as correspondências, para obter um recibo com sua lista de estudos elegíveis.",
    placeholder: "Digite sua resposta ou descreva-se…",
    allDone: "Pronto — mostrar meu relatório",
    fit: "Parece adequado",
    closer: "Vale uma olhada mais de perto",
    searching: [
      "Pesquisando ensaios…",
      "Expandindo termos simples…",
      "Lendo os critérios de elegibilidade…",
      "Verificando os centros que recrutam…",
      "Refinando a lista…",
    ],
  },
  zh: {
    intro:
      "您好！我可以帮您查找马萨诸塞州正在招募的临床试验。" +
      "请用简单的话介绍一下自己，例如年龄、病情和居住的城镇。" +
      "我会搜索试验，列出看起来合适的，并一次问您一个问题来缩小范围。" +
      "您输入的内容不会保存在我们的服务器上。这不是医疗建议，最终决定始终由研究协调员做出。" +
      "当您对匹配结果满意时，随时可以点击“完成 — 显示我的报告”，获取您符合条件的研究清单收据。",
    placeholder: "输入您的回答或介绍自己…",
    allDone: "完成 — 显示我的报告",
    fit: "看起来合适",
    closer: "值得进一步了解",
    searching: [
      "正在搜索试验…",
      "正在扩展通俗术语…",
      "正在阅读入选标准…",
      "正在检查招募中心…",
      "正在筛选名单…",
    ],
  },
  ht: {
    intro:
      "Bonjou! Mwen ka ede w jwenn esè klinik ki ap rekrite nan Massachusetts. " +
      "Pale m yon ti jan de tèt ou nan mo senp, pa egzanp laj ou, kondisyon sante w ak vil kote w ap viv la. " +
      "M ap chèche esè yo, montre w sa ki sanble ap bon pou ou, epi poze w yon kesyon alafwa. " +
      "Anyen ou tape pa sere sou sèvè nou an. Sa a pa konsèy medikal: kowòdonatè etid la toujou pran desizyon final la." +
      " Ou ka klike sou \"Fini — montre rapò m\" nenpòt ki lè ou satisfè ak rezilta yo, pou jwenn yon resi lis etid ou kalifye yo.",
    placeholder: "Tape repons ou oswa dekri tèt ou…",
    allDone: "Fini — montre rapò m",
    fit: "Sanble ap bon",
    closer: "Vo la pen gade pi pre",
    searching: [
      "Ap chèche esè yo…",
      "Ap elaji mo senp yo…",
      "Ap li kritè kalifikasyon yo…",
      "Ap tcheke sant k ap rekrite yo…",
      "Ap redui lis la…",
    ],
  },
  vi: {
    intro:
      "Xin chào! Tôi có thể giúp bạn tìm các thử nghiệm lâm sàng đang tuyển người tại Massachusetts. " +
      "Hãy kể đôi chút về bản thân bằng lời đơn giản, ví dụ tuổi, bệnh của bạn và thị trấn bạn sống. " +
      "Tôi sẽ tìm các thử nghiệm, cho bạn thấy những thử nghiệm có vẻ phù hợp và hỏi từng câu một để thu hẹp lại. " +
      "Những gì bạn gõ không được lưu trên máy chủ của chúng tôi. Đây không phải lời khuyên y tế: điều phối viên nghiên cứu luôn là người quyết định cuối cùng." +
      " Bạn có thể nhấp vào \"Xong — hiển thị báo cáo của tôi\" bất cứ lúc nào khi hài lòng với kết quả, để nhận biên nhận danh sách các nghiên cứu đủ điều kiện của bạn.",
    placeholder: "Nhập câu trả lời hoặc mô tả bản thân…",
    allDone: "Xong — hiển thị báo cáo của tôi",
    fit: "Có vẻ phù hợp",
    closer: "Đáng xem kỹ hơn",
    searching: [
      "Đang tìm thử nghiệm…",
      "Đang mở rộng từ ngữ đơn giản…",
      "Đang đọc tiêu chí đủ điều kiện…",
      "Đang kiểm tra các trung tâm tuyển người…",
      "Đang thu hẹp danh sách…",
    ],
  },
};
