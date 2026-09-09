"""Chat/Template 렌더러 다국어 카탈로그 (SSOT).

구조는 **키 중심**이다: ``code -> {locale: text}``.
새 룰을 추가하면 이 파일에 코드 1개를 추가하되 SUPPORTED_LOCALES 전부를 채워야 한다.
빠뜨리면 tests/unit/test_renderer_i18n_complete.py 가 로케일별 누락을 찍으며 실패한다.

왜 키 중심인가:
    로케일 중심(dict per locale)이면 새 코드 1개당 7곳을 고쳐야 해서 드리프트가 난다.
    실제로 이 구조 이전엔 en/ko 2종만 있었고 zh/es/vi/th/pt 는 전부 영어로 폴백되고 있었다
    (renderer.py 의 ``_CAUSE_KO if locale == "ko" else _CAUSE_EN`` 이진 분기).

폴백 순서: 요청 로케일 -> en -> 코드를 humanize(Title Case).
"""
from __future__ import annotations

# 앱/웹이 지원하는 표시 언어. 새 언어를 추가하면 카탈로그 전체를 채워야 한다.
SUPPORTED_LOCALES: tuple[str, ...] = ("en", "ko", "zh", "es", "vi", "th", "pt")
DEFAULT_LOCALE = "en"

# 어떤 intent 키워드에도 걸리지 않은 질문. renderer/chat_service 가 공유한다.
UNKNOWN_INTENT = "unknown"

# "pt-BR" / "zh_Hans" / "EN" 같은 변형을 지원 로케일로 접는다.
_ALIASES = {
    "pt-br": "pt", "zh-hans": "zh", "zh-cn": "zh", "zh-hant": "zh", "zh-tw": "zh",
}


def normalize_locale(locale: str | None) -> str:
    """요청 로케일을 지원 로케일 코드로 정규화. 모르면 DEFAULT_LOCALE."""
    if not locale:
        return DEFAULT_LOCALE
    raw = locale.strip().lower().replace("_", "-")
    if raw in _ALIASES:
        return _ALIASES[raw]
    if raw in SUPPORTED_LOCALES:
        return raw
    base = raw.split("-", 1)[0]
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def label(catalog: dict[str, dict[str, str]], code: str, locale: str) -> str:
    """코드 -> 해당 로케일 라벨. 로케일 누락은 en, 코드 자체가 미등록이면 humanize."""
    entry = catalog.get(code)
    if not entry:
        return code.replace("_", " ").title()
    return entry.get(locale) or entry.get(DEFAULT_LOCALE) or code.replace("_", " ").title()


def ui(key: str, locale: str) -> str:
    """렌더러가 쓰는 고정 문구(섹션 라벨/심각도/안내문)."""
    return label(UI_LABELS, key, locale)


# ── 원인(cause) 라벨 ──────────────────────────────────────────────────────────
CAUSE_LABELS: dict[str, dict[str, str]] = {
    "aging_sow_herd_high_parity_share": {
        "en": "Aging herd — high share of parity 7+", "ko": "노산돈(7산 이상) 비율 과다",
        "zh": "母猪群老龄化——7胎以上占比过高", "es": "Piara envejecida: alta proporción de parto 7+",
        "vi": "Đàn nái già — tỷ lệ lứa 7 trở lên quá cao",
        "th": "ฝูงแม่สุกรอายุมาก — สัดส่วนครอกที่ 7 ขึ้นไปสูง",
        "pt": "Plantel envelhecido — alta proporção de ordem de parto 7+"},
    "batch_managed_farm_detected": {
        "en": "Batch (all-in-all-out) management detected", "ko": "배치(올인올아웃) 운영 감지",
        "zh": "检测到批次化(全进全出)管理", "es": "Gestión por lotes (todo dentro-todo fuera) detectada",
        "vi": "Phát hiện quản lý theo lô (cùng vào cùng ra)",
        "th": "ตรวจพบการจัดการแบบรุ่น (เข้าพร้อมกัน-ออกพร้อมกัน)",
        "pt": "Manejo em lotes (todos dentro-todos fora) detectado"},
    "critically_low_litter_size_or_survivability": {
        "en": "Critically low litter size or survivability", "ko": "복당 두수 또는 생존율 심각 저하",
        "zh": "窝产仔数或存活率严重偏低", "es": "Tamaño de camada o supervivencia críticamente bajos",
        "vi": "Số con/ổ hoặc tỷ lệ sống thấp nghiêm trọng",
        "th": "จำนวนลูกต่อครอกหรืออัตรารอดต่ำวิกฤต",
        "pt": "Tamanho de leitegada ou sobrevivência criticamente baixos"},
    "daily_gain_decreased": {
        "en": "Decreased daily weight gain", "ko": "일당 증체량 감소",
        "zh": "日增重下降", "es": "Descenso de la ganancia diaria de peso",
        "vi": "Tăng trọng bình quân ngày giảm", "th": "อัตราการเจริญเติบโตต่อวันลดลง",
        "pt": "Queda no ganho de peso diário"},
    "elevated_abortion_rate": {
        "en": "Elevated abortion rate", "ko": "유산율 상승",
        "zh": "流产率升高", "es": "Tasa de abortos elevada",
        "vi": "Tỷ lệ sảy thai tăng cao", "th": "อัตราการแท้งสูงขึ้น",
        "pt": "Taxa de aborto elevada"},
    "elevated_return_to_service_rate": {
        "en": "Elevated return-to-service rate", "ko": "재발정율(재교배율) 상승",
        "zh": "返情率升高", "es": "Tasa de repeticiones de cubrición elevada",
        "vi": "Tỷ lệ phối lại tăng cao", "th": "อัตราการกลับสัดหลังผสมสูงขึ้น",
        "pt": "Taxa de retorno ao cio elevada"},
    "excessive_sow_replacement": {
        "en": "Excessive sow replacement rate", "ko": "모돈 갱신율 과다",
        "zh": "母猪更新率过高", "es": "Tasa de reposición de cerdas excesiva",
        "vi": "Tỷ lệ thay đàn nái quá cao", "th": "อัตราการทดแทนแม่สุกรสูงเกินไป",
        "pt": "Taxa de reposição de matrizes excessiva"},
    "extended_return_to_estrus": {
        "en": "Extended return to estrus", "ko": "발정 재귀 지연",
        "zh": "返情间隔延长", "es": "Retorno al celo prolongado",
        "vi": "Thời gian động dục trở lại kéo dài", "th": "การกลับมาเป็นสัดล่าช้า",
        "pt": "Retorno ao cio prolongado"},
    "farm_grade_green": {
        "en": "Farm overall grade: GREEN (good)", "ko": "농가 종합등급: GREEN(양호)",
        "zh": "猪场综合等级：GREEN(良好)", "es": "Calificación global de la granja: VERDE (buena)",
        "vi": "Xếp loại tổng thể trại: XANH (tốt)", "th": "เกรดรวมของฟาร์ม: เขียว (ดี)",
        "pt": "Classificação geral da granja: VERDE (boa)"},
    "farm_grade_red": {
        "en": "Farm overall grade: RED (urgent)", "ko": "농가 종합등급: RED(시급)",
        "zh": "猪场综合等级：RED(紧急)", "es": "Calificación global de la granja: ROJA (urgente)",
        "vi": "Xếp loại tổng thể trại: ĐỎ (khẩn cấp)", "th": "เกรดรวมของฟาร์ม: แดง (เร่งด่วน)",
        "pt": "Classificação geral da granja: VERMELHA (urgente)"},
    "farm_grade_yellow": {
        "en": "Farm overall grade: YELLOW (watch)", "ko": "농가 종합등급: YELLOW(주의)",
        "zh": "猪场综合等级：YELLOW(需关注)", "es": "Calificación global de la granja: AMARILLA (vigilar)",
        "vi": "Xếp loại tổng thể trại: VÀNG (cần theo dõi)", "th": "เกรดรวมของฟาร์ม: เหลือง (ต้องเฝ้าระวัง)",
        "pt": "Classificação geral da granja: AMARELA (atenção)"},
    "feed_intake_increased": {
        "en": "Increased feed intake with no gain improvement", "ko": "사료 섭취량 증가 (증체 미개선)",
        "zh": "采食量增加但增重未改善", "es": "Mayor consumo de pienso sin mejora de ganancia",
        "vi": "Lượng ăn tăng nhưng tăng trọng không cải thiện",
        "th": "ปริมาณอาหารที่กินเพิ่มขึ้นแต่การเจริญเติบโตไม่ดีขึ้น",
        "pt": "Maior consumo de ração sem melhora de ganho"},
    "high_crushing_death_rate": {
        "en": "High piglet crushing-death rate", "ko": "압사 폐사율 과다",
        "zh": "仔猪压死率过高", "es": "Alta tasa de muerte por aplastamiento",
        "vi": "Tỷ lệ heo con bị đè chết cao", "th": "อัตราลูกสุกรถูกแม่ทับตายสูง",
        "pt": "Alta taxa de morte por esmagamento"},
    "high_feed_conversion_ratio": {
        "en": "High feed conversion ratio", "ko": "사료요구율(FCR) 과다",
        "zh": "料肉比过高", "es": "Índice de conversión alimenticia elevado",
        "vi": "Hệ số chuyển hóa thức ăn (FCR) cao", "th": "อัตราแลกเนื้อ (FCR) สูง",
        "pt": "Conversão alimentar elevada"},
    "high_finishing_mortality": {
        "en": "High finishing mortality", "ko": "비육 폐사율 과다",
        "zh": "育肥阶段死亡率过高", "es": "Alta mortalidad en engorde",
        "vi": "Tỷ lệ chết ở giai đoạn vỗ béo cao", "th": "อัตราการตายในระยะขุนสูง",
        "pt": "Alta mortalidade na terminação"},
    "high_mummified_rate": {
        "en": "High mummified-fetus rate", "ko": "미라변성태 과다",
        "zh": "木乃伊胎比例过高", "es": "Alta tasa de fetos momificados",
        "vi": "Tỷ lệ thai khô (mummy) cao", "th": "อัตราลูกมัมมี่สูง",
        "pt": "Alta taxa de fetos mumificados"},
    "high_non_productive_days_extending_inter_litter_interval": {
        "en": "High NPD extending inter-litter interval", "ko": "NPD 과다로 분만간격 연장",
        "zh": "非生产天数过多导致产仔间隔延长", "es": "DNP elevados que alargan el intervalo entre partos",
        "vi": "Ngày không sản xuất (NPD) cao làm kéo dài khoảng cách lứa đẻ",
        "th": "วันไม่ให้ผลผลิต (NPD) สูง ทำให้ช่วงห่างระหว่างครอกยาวขึ้น",
        "pt": "DNP elevados alongando o intervalo entre partos"},
    "high_pre_weaning_piglet_mortality": {
        "en": "High pre-weaning piglet mortality", "ko": "포유자돈 폐사 과다",
        "zh": "哺乳仔猪死亡率过高", "es": "Alta mortalidad de lechones predestete",
        "vi": "Tỷ lệ heo con chết trước cai sữa cao", "th": "อัตราการตายของลูกสุกรก่อนหย่านมสูง",
        "pt": "Alta mortalidade de leitões pré-desmame"},
    "high_sow_culling_rate": {
        "en": "High sow culling rate", "ko": "모돈 도태율 과다",
        "zh": "母猪淘汰率过高", "es": "Alta tasa de eliminación de cerdas",
        "vi": "Tỷ lệ loại thải nái cao", "th": "อัตราการคัดทิ้งแม่สุกรสูง",
        "pt": "Alta taxa de descarte de matrizes"},
    "high_sow_mortality": {
        "en": "High sow mortality", "ko": "모돈 폐사율 과다",
        "zh": "母猪死亡率过高", "es": "Alta mortalidad de cerdas",
        "vi": "Tỷ lệ nái chết cao", "th": "อัตราการตายของแม่สุกรสูง",
        "pt": "Alta mortalidade de matrizes"},
    "high_stillbirth_rate": {
        "en": "High stillbirth rate", "ko": "사산율 과다",
        "zh": "死胎率过高", "es": "Alta tasa de nacidos muertos",
        "vi": "Tỷ lệ thai chết lưu cao", "th": "อัตราลูกตายแรกคลอดสูง",
        "pt": "Alta taxa de natimortos"},
    "high_weaning_to_mating_interval": {
        "en": "High weaning-to-mating interval", "ko": "이유~교배 간격 과다",
        "zh": "断奶至配种间隔过长", "es": "Intervalo destete-cubrición elevado",
        "vi": "Khoảng cách cai sữa đến phối giống dài", "th": "ช่วงหย่านมถึงผสมพันธุ์ยาวเกินไป",
        "pt": "Intervalo desmame-cobertura elevado"},
    "insufficient_sow_replacement": {
        "en": "Insufficient sow replacement rate", "ko": "모돈 갱신율 과소",
        "zh": "母猪更新率不足", "es": "Tasa de reposición de cerdas insuficiente",
        "vi": "Tỷ lệ thay đàn nái không đủ", "th": "อัตราการทดแทนแม่สุกรต่ำเกินไป",
        "pt": "Taxa de reposição de matrizes insuficiente"},
    "insufficient_weaning_records": {
        "en": "Insufficient weaning records", "ko": "이유 기록 부족",
        "zh": "断奶记录不足", "es": "Registros de destete insuficientes",
        "vi": "Thiếu dữ liệu cai sữa", "th": "ข้อมูลการหย่านมไม่เพียงพอ",
        "pt": "Registros de desmame insuficientes"},
    "lactation_length_too_long": {
        "en": "Lactation length too long", "ko": "포유기간 과다",
        "zh": "哺乳期过长", "es": "Duración de la lactación demasiado larga",
        "vi": "Thời gian nuôi con quá dài", "th": "ระยะการให้นมยาวเกินไป",
        "pt": "Duração da lactação muito longa"},
    "lactation_length_too_short": {
        "en": "Lactation length too short", "ko": "포유기간 과소(조기이유)",
        "zh": "哺乳期过短(早期断奶)", "es": "Duración de la lactación demasiado corta (destete precoz)",
        "vi": "Thời gian nuôi con quá ngắn (cai sữa sớm)", "th": "ระยะการให้นมสั้นเกินไป (หย่านมเร็ว)",
        "pt": "Duração da lactação muito curta (desmame precoce)"},
    "low_average_birth_weight": {
        "en": "Low average birth weight", "ko": "평균 출생체중 저하",
        "zh": "平均初生重偏低", "es": "Peso medio al nacimiento bajo",
        "vi": "Khối lượng sơ sinh bình quân thấp", "th": "น้ำหนักแรกเกิดเฉลี่ยต่ำ",
        "pt": "Peso médio ao nascimento baixo"},
    "low_average_daily_gain": {
        "en": "Low average daily gain", "ko": "일당증체(ADG) 저조",
        "zh": "平均日增重偏低", "es": "Ganancia media diaria baja",
        "vi": "Tăng trọng bình quân ngày (ADG) thấp", "th": "อัตราการเจริญเติบโตต่อวัน (ADG) ต่ำ",
        "pt": "Ganho de peso diário baixo"},
    "low_boar_farrowing_rate": {
        "en": "Low farrowing rate for this boar", "ko": "해당 웅돈 분만율 저조",
        "zh": "该公猪对应分娩率偏低", "es": "Tasa de partos baja para este verraco",
        "vi": "Tỷ lệ đẻ thấp ở đực giống này", "th": "อัตราการคลอดต่ำสำหรับพ่อพันธุ์ตัวนี้",
        "pt": "Taxa de parto baixa para este cachaço"},
    "low_born_alive_per_litter": {
        "en": "Low born-alive per litter", "ko": "복당 실산자 부족",
        "zh": "窝均活产仔数偏低", "es": "Pocos nacidos vivos por camada",
        "vi": "Số con sơ sinh sống trên ổ thấp", "th": "จำนวนลูกเกิดมีชีวิตต่อครอกต่ำ",
        "pt": "Poucos nascidos vivos por leitegada"},
    "low_conception_rate": {
        "en": "Low conception rate (pregnancy-check positive)", "ko": "수태율 저조(임신감정 양성)",
        "zh": "受胎率偏低(妊娠鉴定阳性)", "es": "Tasa de concepción baja (diagnóstico de gestación positivo)",
        "vi": "Tỷ lệ thụ thai thấp (khám thai dương tính)", "th": "อัตราการผสมติดต่ำ (ตรวจการตั้งท้องเป็นบวก)",
        "pt": "Taxa de concepção baixa (diagnóstico de gestação positivo)"},
    "low_litters_per_sow_per_year": {
        "en": "Low litters per sow per year", "ko": "모돈당 연간 산차수 저조",
        "zh": "每头母猪年产窝数偏低", "es": "Pocos partos por cerda y año",
        "vi": "Số lứa đẻ trên nái mỗi năm thấp", "th": "จำนวนครอกต่อแม่สุกรต่อปีต่ำ",
        "pt": "Poucos partos por matriz por ano"},
    "low_piglets_weaned_per_litter": {
        "en": "Low piglets weaned per litter", "ko": "복당 이유두수 부족",
        "zh": "窝均断奶仔猪数偏低", "es": "Pocos lechones destetados por camada",
        "vi": "Số heo con cai sữa trên ổ thấp", "th": "จำนวนลูกหย่านมต่อครอกต่ำ",
        "pt": "Poucos leitões desmamados por leitegada"},
    "low_total_born_per_litter": {
        "en": "Low total-born per litter", "ko": "복당 총산자 부족",
        "zh": "窝均总产仔数偏低", "es": "Pocos nacidos totales por camada",
        "vi": "Tổng số con sinh ra trên ổ thấp", "th": "จำนวนลูกเกิดทั้งหมดต่อครอกต่ำ",
        "pt": "Poucos nascidos totais por leitegada"},
    "low_weaning_weight": {
        "en": "Low weaning weight", "ko": "이유체중 저하",
        "zh": "断奶重偏低", "es": "Peso al destete bajo",
        "vi": "Khối lượng cai sữa thấp", "th": "น้ำหนักหย่านมต่ำ",
        "pt": "Peso ao desmame baixo"},
    "mortality_increased": {
        "en": "Elevated mortality in finishing groups", "ko": "비육돈 폐사율 상승",
        "zh": "育肥群死亡率升高", "es": "Mortalidad elevada en lotes de engorde",
        "vi": "Tỷ lệ chết ở nhóm vỗ béo tăng", "th": "อัตราการตายในกลุ่มสุกรขุนสูงขึ้น",
        "pt": "Mortalidade elevada nos lotes de terminação"},
    "msy_below_breakeven": {
        "en": "MSY below break-even (marketed pigs/sow/year)", "ko": "MSY 손익분기 미달(연간 출하/모돈)",
        "zh": "MSY低于盈亏平衡(年出栏头数/母猪)",
        "es": "MSY por debajo del punto de equilibrio (cerdos vendidos/cerda/año)",
        "vi": "MSY dưới điểm hòa vốn (heo xuất chuồng/nái/năm)",
        "th": "MSY ต่ำกว่าจุดคุ้มทุน (สุกรขายต่อแม่ต่อปี)",
        "pt": "MSY abaixo do ponto de equilíbrio (suínos vendidos/matriz/ano)"},
    "no_active_sows_registered_in_system": {
        "en": "No active sows registered in the system", "ko": "시스템에 등록된 활성 모돈 없음",
        "zh": "系统中没有在群母猪记录", "es": "No hay cerdas activas registradas en el sistema",
        "vi": "Chưa có nái đang hoạt động nào trong hệ thống", "th": "ไม่มีแม่สุกรที่ใช้งานอยู่ในระบบ",
        "pt": "Nenhuma matriz ativa registrada no sistema"},
    "npd_nonproductive_days_economic_loss": {
        "en": "Economic loss from non-productive days (WEI)", "ko": "비생산일(WEI) 경제 손실",
        "zh": "非生产天数(断奶至配种间隔)造成的经济损失",
        "es": "Pérdida económica por días no productivos (IDC)",
        "vi": "Thiệt hại kinh tế do ngày không sản xuất (WEI)",
        "th": "ความสูญเสียทางเศรษฐกิจจากวันไม่ให้ผลผลิต (WEI)",
        "pt": "Perda econômica por dias não produtivos (IDC)"},
    "possible_abortive_disease": {
        "en": "Possible abortive disease (lepto/parvo/PRRS)", "ko": "유산성 질병 의심(렙토/파보/PRRS)",
        "zh": "疑似流产性疾病(钩端螺旋体/细小病毒/蓝耳)", "es": "Posible enfermedad abortiva (lepto/parvo/PRRS)",
        "vi": "Nghi bệnh gây sảy thai (lepto/parvo/PRRS)", "th": "สงสัยโรคที่ทำให้แท้ง (เลปโต/พาร์โว/PRRS)",
        "pt": "Possível doença abortiva (lepto/parvo/PRRS)"},
    "possible_disease_causing_early_embryo_loss_or_abortion": {
        "en": "Possible disease causing embryo loss/abortion", "ko": "질병으로 인한 수정란 손실/유산 의심",
        "zh": "疑似疾病导致胚胎损失或流产", "es": "Posible enfermedad causante de pérdida embrionaria/aborto",
        "vi": "Nghi bệnh gây mất phôi/sảy thai", "th": "สงสัยโรคที่ทำให้สูญเสียตัวอ่อนหรือแท้ง",
        "pt": "Possível doença causando perda embrionária/aborto"},
    "possible_disease_or_management_failure": {
        "en": "Possible disease or management failure", "ko": "질병 또는 관리 실패 의심",
        "zh": "疑似疾病或管理失误", "es": "Posible enfermedad o fallo de manejo",
        "vi": "Nghi do bệnh hoặc sai sót quản lý", "th": "สงสัยโรคหรือความผิดพลาดในการจัดการ",
        "pt": "Possível doença ou falha de manejo"},
    "possible_disease_outbreak_in_finishing": {
        "en": "Possible disease outbreak in finishing", "ko": "비육돈 질병 발생 의심",
        "zh": "疑似育肥阶段疫病暴发", "es": "Posible brote de enfermedad en engorde",
        "vi": "Nghi bùng phát dịch bệnh ở giai đoạn vỗ béo", "th": "สงสัยการระบาดของโรคในระยะขุน",
        "pt": "Possível surto de doença na terminação"},
    "possible_farrowing_management_or_low_vitality_piglets": {
        "en": "Possible farrowing management or low-vitality piglets", "ko": "분만관리 또는 저활력 자돈 의심",
        "zh": "疑似分娩管理不当或仔猪活力低",
        "es": "Posible manejo del parto deficiente o lechones poco vitales",
        "vi": "Nghi do quản lý đẻ hoặc heo con yếu sức sống",
        "th": "สงสัยการจัดการคลอดหรือลูกสุกรมีความแข็งแรงต่ำ",
        "pt": "Possível manejo de parto inadequado ou leitões de baixa vitalidade"},
    "possible_high_embryonic_loss": {
        "en": "Possible high embryonic loss", "ko": "수정란 손실 과다 의심",
        "zh": "疑似胚胎损失过高", "es": "Posible pérdida embrionaria elevada",
        "vi": "Nghi mất phôi nhiều", "th": "สงสัยการสูญเสียตัวอ่อนสูง",
        "pt": "Possível perda embrionária elevada"},
    "possible_in_utero_viral_infection": {
        "en": "Possible in-utero viral infection (PPV/PRRS)", "ko": "자궁 내 바이러스 감염 의심(PPV/PRRS)",
        "zh": "疑似子宫内病毒感染(猪细小病毒/蓝耳)", "es": "Posible infección vírica intrauterina (PPV/PRRS)",
        "vi": "Nghi nhiễm virus trong tử cung (PPV/PRRS)", "th": "สงสัยการติดเชื้อไวรัสในมดลูก (PPV/PRRS)",
        "pt": "Possível infecção viral intrauterina (PPV/PRRS)"},
    "possible_involuntary_culling_from_reproductive_failure": {
        "en": "Possible involuntary culling from reproductive failure", "ko": "번식장애로 인한 비자발 도태 의심",
        "zh": "疑似因繁殖障碍导致的被动淘汰",
        "es": "Posible eliminación involuntaria por fallo reproductivo",
        "vi": "Nghi loại thải bắt buộc do rối loạn sinh sản",
        "th": "สงสัยการคัดทิ้งโดยจำเป็นจากปัญหาระบบสืบพันธุ์",
        "pt": "Possível descarte involuntário por falha reprodutiva"},
    "possible_large_litter_or_poor_late_gestation_feeding": {
        "en": "Possible large litter or poor late-gestation feeding",
        "ko": "과다 복수 또는 임신후기 급이 부족 의심",
        "zh": "疑似窝产仔过多或妊娠后期饲喂不足",
        "es": "Posible camada numerosa o alimentación deficiente en gestación tardía",
        "vi": "Nghi ổ quá đông hoặc cho ăn cuối thai kỳ chưa đủ",
        "th": "สงสัยครอกใหญ่เกินไปหรือให้อาหารช่วงท้ายการตั้งท้องไม่พอ",
        "pt": "Possível leitegada numerosa ou alimentação deficiente no final da gestação"},
    "possible_poor_farrowing_management_or_sow_agitation": {
        "en": "Possible poor farrowing management or sow agitation", "ko": "분만관리 미흡 또는 모돈 불안 의심",
        "zh": "疑似分娩管理不足或母猪躁动",
        "es": "Posible manejo del parto deficiente o nerviosismo de la cerda",
        "vi": "Nghi quản lý đẻ chưa tốt hoặc nái bị kích động",
        "th": "สงสัยการจัดการคลอดไม่ดีหรือแม่สุกรตื่นตกใจ",
        "pt": "Possível manejo de parto deficiente ou agitação da matriz"},
    "possible_prolonged_farrowing_or_late_gestation_disease": {
        "en": "Possible prolonged farrowing or late-gestation disease", "ko": "난산 또는 임신후기 질병 의심",
        "zh": "疑似产程过长或妊娠后期疾病",
        "es": "Posible parto prolongado o enfermedad en gestación tardía",
        "vi": "Nghi đẻ khó kéo dài hoặc bệnh cuối thai kỳ",
        "th": "สงสัยการคลอดยืดเยื้อหรือโรคช่วงท้ายการตั้งท้อง",
        "pt": "Possível parto prolongado ou doença no final da gestação"},
    "possible_reproductive_disease_in_gilts": {
        "en": "Possible reproductive disease in gilts", "ko": "후보돈 번식질환 의심",
        "zh": "疑似后备母猪繁殖性疾病", "es": "Posible enfermedad reproductiva en cerdas de reposición",
        "vi": "Nghi bệnh sinh sản ở nái hậu bị", "th": "สงสัยโรคระบบสืบพันธุ์ในสุกรสาวทดแทน",
        "pt": "Possível doença reprodutiva em leitoas"},
    "possible_subclinical_disease_depressing_efficiency": {
        "en": "Possible subclinical disease depressing efficiency", "ko": "준임상 질병으로 사료효율 저하 의심",
        "zh": "疑似亚临床疾病拉低饲料效率", "es": "Posible enfermedad subclínica que reduce la eficiencia",
        "vi": "Nghi bệnh cận lâm sàng làm giảm hiệu quả thức ăn",
        "th": "สงสัยโรคแฝงทำให้ประสิทธิภาพอาหารลดลง",
        "pt": "Possível doença subclínica reduzindo a eficiência"},
    "possible_subclinical_disease_depressing_growth": {
        "en": "Possible subclinical disease depressing growth", "ko": "준임상 질병으로 증체 저하 의심",
        "zh": "疑似亚临床疾病抑制生长", "es": "Posible enfermedad subclínica que frena el crecimiento",
        "vi": "Nghi bệnh cận lâm sàng làm giảm tăng trưởng", "th": "สงสัยโรคแฝงทำให้การเจริญเติบโตลดลง",
        "pt": "Possível doença subclínica reduzindo o crescimento"},
    "pregnancy_accident_economic_loss": {
        "en": "Economic loss from pregnancy accidents", "ko": "임신사고 경제 손실",
        "zh": "妊娠事故造成的经济损失", "es": "Pérdida económica por incidencias de gestación",
        "vi": "Thiệt hại kinh tế do sự cố mang thai",
        "th": "ความสูญเสียทางเศรษฐกิจจากอุบัติการณ์ระหว่างตั้งท้อง",
        "pt": "Perda econômica por acidentes de gestação"},
    "pregnancy_accidents_concentrated_in_p1": {
        "en": "Pregnancy accidents concentrated in parity 1", "ko": "임신사고 1산차 편중",
        "zh": "妊娠事故集中于第1胎", "es": "Incidencias de gestación concentradas en el parto 1",
        "vi": "Sự cố mang thai tập trung ở lứa 1",
        "th": "อุบัติการณ์ระหว่างตั้งท้องกระจุกตัวที่ครอกที่ 1",
        "pt": "Acidentes de gestação concentrados na ordem de parto 1"},
    "premature_sow_culling_economic_loss": {
        "en": "Economic loss from premature sow culling", "ko": "조기도태 경제 손실",
        "zh": "母猪过早淘汰造成的经济损失", "es": "Pérdida económica por eliminación prematura de cerdas",
        "vi": "Thiệt hại kinh tế do loại thải nái sớm",
        "th": "ความสูญเสียทางเศรษฐกิจจากการคัดทิ้งแม่สุกรก่อนกำหนด",
        "pt": "Perda econômica por descarte precoce de matrizes"},
    "preweaning_deaths_concentrated_first_3_days": {
        "en": "Pre-weaning deaths concentrated in first 3 days", "ko": "생후 3일내 폐사 편중",
        "zh": "断奶前死亡集中在出生后3天内", "es": "Muertes predestete concentradas en los 3 primeros días",
        "vi": "Heo con chết trước cai sữa tập trung trong 3 ngày đầu",
        "th": "การตายก่อนหย่านมกระจุกใน 3 วันแรก",
        "pt": "Mortes pré-desmame concentradas nos 3 primeiros dias"},
    "preweaning_mortality_economic_loss": {
        "en": "Economic loss from pre-weaning mortality", "ko": "포유자돈 폐사 경제 손실",
        "zh": "哺乳仔猪死亡造成的经济损失", "es": "Pérdida económica por mortalidad predestete",
        "vi": "Thiệt hại kinh tế do heo con chết trước cai sữa",
        "th": "ความสูญเสียทางเศรษฐกิจจากการตายก่อนหย่านม",
        "pt": "Perda econômica por mortalidade pré-desmame"},
    "prolonged_weaning_to_service_interval": {
        "en": "Prolonged weaning-to-service interval", "ko": "이유~재교배 간격 지연",
        "zh": "断奶至配种间隔延长", "es": "Intervalo destete-cubrición prolongado",
        "vi": "Khoảng cách cai sữa đến phối giống kéo dài", "th": "ช่วงหย่านมถึงผสมพันธุ์ยืดยาว",
        "pt": "Intervalo desmame-cobertura prolongado"},
    "repeat_breeding_failures": {
        "en": "Repeat breeding failures", "ko": "반복 교배 실패",
        "zh": "反复配种失败", "es": "Fallos de cubrición repetidos",
        "vi": "Phối giống thất bại lặp lại", "th": "การผสมพันธุ์ไม่ติดซ้ำหลายครั้ง",
        "pt": "Falhas repetidas de cobertura"},
    "repeat_breeding_failures_extending_cycle": {
        "en": "Repeat breeding failures extending cycle", "ko": "반복 교배 실패로 사이클 연장",
        "zh": "反复配种失败导致周期延长", "es": "Fallos de cubrición repetidos que alargan el ciclo",
        "vi": "Phối giống thất bại lặp lại làm kéo dài chu kỳ",
        "th": "การผสมไม่ติดซ้ำทำให้รอบการผลิตยาวขึ้น",
        "pt": "Falhas repetidas de cobertura alongando o ciclo"},
    "seasonal_summer_infertility": {
        "en": "Seasonal summer infertility (farrowing-rate drop)", "ko": "여름철 계절성 불임(분만율 하락)",
        "zh": "季节性夏季不孕(分娩率下降)", "es": "Infertilidad estival estacional (caída de la tasa de partos)",
        "vi": "Vô sinh mùa hè theo mùa (tỷ lệ đẻ giảm)",
        "th": "ภาวะผสมไม่ติดตามฤดูกาลในหน้าร้อน (อัตราการคลอดลดลง)",
        "pt": "Infertilidade sazonal de verão (queda na taxa de parto)"},
    "second_litter_slump": {
        "en": "Second-litter slump (P2 born-alive drop vs P1)", "ko": "2산차 슬럼프(P2 실산 감소)",
        "zh": "二胎综合征(第2胎活产仔数低于第1胎)",
        "es": "Síndrome del segundo parto (caída de nacidos vivos P2 frente a P1)",
        "vi": "Suy giảm lứa 2 (số con sống lứa 2 giảm so với lứa 1)",
        "th": "ภาวะครอกที่สองตก (ลูกเกิดมีชีวิตครอก 2 ลดลงเทียบครอก 1)",
        "pt": "Síndrome do segundo parto (queda de nascidos vivos na OP2 vs OP1)"},
    "severe_heat_stress_depressing_conception": {
        "en": "Severe heat stress depressing conception", "ko": "고온스트레스로 수태 저하",
        "zh": "严重热应激抑制受胎", "es": "Estrés térmico severo que reduce la concepción",
        "vi": "Stress nhiệt nghiêm trọng làm giảm tỷ lệ thụ thai",
        "th": "ความเครียดจากความร้อนรุนแรงทำให้การผสมติดลดลง",
        "pt": "Estresse térmico severo reduzindo a concepção"},
    "weakest_kpi_priority": {
        "en": "Most urgent KPI to address first", "ko": "가장 먼저 개선할 KPI",
        "zh": "最应优先改善的KPI", "es": "KPI más urgente a abordar primero",
        "vi": "Chỉ số KPI cần ưu tiên cải thiện trước", "th": "KPI ที่ต้องแก้ไขก่อนเป็นอันดับแรก",
        "pt": "KPI mais urgente a tratar primeiro"},
}

# ── 조치(action) 라벨 ─────────────────────────────────────────────────────────
ACTION_LABELS: dict[str, dict[str, str]] = {
    "adjust_weaning_age_to_target": {
        "en": "Adjust weaning age toward target", "ko": "이유일령 목표 조정",
        "zh": "将断奶日龄调整至目标值", "es": "Ajustar la edad al destete hacia el objetivo",
        "vi": "Điều chỉnh tuổi cai sữa về mức mục tiêu", "th": "ปรับอายุหย่านมให้เข้าเป้าหมาย",
        "pt": "Ajustar a idade ao desmame para a meta"},
    "audit_feed_quality_and_mycotoxins": {
        "en": "Audit feed quality and mycotoxins", "ko": "사료 품질·곰팡이독소 점검",
        "zh": "检查饲料品质与霉菌毒素", "es": "Auditar la calidad del pienso y las micotoxinas",
        "vi": "Kiểm tra chất lượng thức ăn và độc tố nấm mốc",
        "th": "ตรวจสอบคุณภาพอาหารและสารพิษจากเชื้อรา",
        "pt": "Auditar qualidade da ração e micotoxinas"},
    "audit_feed_quality_and_wastage": {
        "en": "Audit feed quality and wastage", "ko": "사료 품질·손실 점검",
        "zh": "检查饲料品质与浪费", "es": "Auditar la calidad del pienso y el desperdicio",
        "vi": "Kiểm tra chất lượng và hao hụt thức ăn", "th": "ตรวจสอบคุณภาพอาหารและการสูญเสียอาหาร",
        "pt": "Auditar qualidade e desperdício de ração"},
    "audit_gilt_breeding_management": {
        "en": "Audit gilt breeding management", "ko": "후보돈 교배 관리 점검",
        "zh": "检查后备母猪配种管理", "es": "Auditar el manejo de cubrición de cerdas de reposición",
        "vi": "Kiểm tra quản lý phối giống nái hậu bị", "th": "ตรวจสอบการจัดการผสมพันธุ์สุกรสาวทดแทน",
        "pt": "Auditar o manejo de cobertura de leitoas"},
    "audit_heat_abatement_and_insemination_timing": {
        "en": "Audit heat abatement and insemination timing", "ko": "고온대책·수정적기 점검",
        "zh": "检查防暑降温措施与输精时机",
        "es": "Auditar las medidas antiestrés térmico y el momento de inseminación",
        "vi": "Kiểm tra biện pháp chống nóng và thời điểm phối tinh",
        "th": "ตรวจสอบมาตรการลดความร้อนและจังหวะการผสมเทียม",
        "pt": "Auditar medidas contra o calor e o momento da inseminação"},
    "audit_heat_detection_and_insemination_timing": {
        "en": "Audit heat detection and insemination timing", "ko": "발정 탐지·수정 적기 점검",
        "zh": "检查发情鉴定与输精时机",
        "es": "Auditar la detección de celo y el momento de inseminación",
        "vi": "Kiểm tra phát hiện động dục và thời điểm phối tinh",
        "th": "ตรวจสอบการจับสัดและจังหวะการผสมเทียม",
        "pt": "Auditar a detecção de cio e o momento da inseminação"},
    "audit_insemination_timing": {
        "en": "Audit insemination timing", "ko": "수정 적기 점검",
        "zh": "检查输精时机", "es": "Auditar el momento de la inseminación",
        "vi": "Kiểm tra thời điểm phối tinh", "th": "ตรวจสอบจังหวะการผสมเทียม",
        "pt": "Auditar o momento da inseminação"},
    "audit_lameness_and_prolapse": {
        "en": "Audit lameness and prolapse", "ko": "지제(파행)·탈출증 점검",
        "zh": "检查跛行与脱垂", "es": "Auditar cojeras y prolapsos",
        "vi": "Kiểm tra què chân và sa tử cung/trực tràng", "th": "ตรวจสอบภาวะขาเจ็บและอวัยวะหลุดยื่น",
        "pt": "Auditar claudicação e prolapsos"},
    "audit_reproductive_failure_and_lameness": {
        "en": "Audit reproductive failure and lameness", "ko": "번식장애·지제(파행) 점검",
        "zh": "检查繁殖障碍与跛行", "es": "Auditar fallos reproductivos y cojeras",
        "vi": "Kiểm tra rối loạn sinh sản và què chân",
        "th": "ตรวจสอบปัญหาระบบสืบพันธุ์และภาวะขาเจ็บ",
        "pt": "Auditar falhas reprodutivas e claudicação"},
    "audit_sow_body_condition_score": {
        "en": "Audit sow body condition score", "ko": "모돈 신체충실지수(BCS) 점검",
        "zh": "检查母猪体况评分(BCS)", "es": "Auditar la condición corporal de las cerdas (BCS)",
        "vi": "Kiểm tra điểm thể trạng nái (BCS)", "th": "ตรวจสอบคะแนนสภาพร่างกายแม่สุกร (BCS)",
        "pt": "Auditar o escore de condição corporal das matrizes (ECC)"},
    "audit_weaning_to_mating_interval": {
        "en": "Audit weaning-to-mating interval", "ko": "이유~교배 간격 점검",
        "zh": "检查断奶至配种间隔", "es": "Auditar el intervalo destete-cubrición",
        "vi": "Kiểm tra khoảng cách cai sữa đến phối giống", "th": "ตรวจสอบช่วงหย่านมถึงผสมพันธุ์",
        "pt": "Auditar o intervalo desmame-cobertura"},
    "check_boar_libido_and_semen_quality": {
        "en": "Check boar libido and semen quality", "ko": "웅돈 성욕·정액 품질 점검",
        "zh": "检查公猪性欲与精液品质", "es": "Comprobar la libido del verraco y la calidad del semen",
        "vi": "Kiểm tra tính hăng và chất lượng tinh dịch của đực giống",
        "th": "ตรวจสอบความต้องการผสมพันธุ์และคุณภาพน้ำเชื้อของพ่อพันธุ์",
        "pt": "Verificar a libido do cachaço e a qualidade do sêmen"},
    "check_feed_waste": {
        "en": "Inspect feeders for waste", "ko": "급이기 사료 낭비 점검",
        "zh": "检查料槽饲料浪费", "es": "Inspeccionar los comederos por desperdicio",
        "vi": "Kiểm tra máng ăn xem có hao hụt thức ăn", "th": "ตรวจรางอาหารเรื่องการสูญเสียอาหาร",
        "pt": "Inspecionar os comedouros quanto a desperdício"},
    "check_semen_handling_and_boar_fertility": {
        "en": "Check semen handling and boar fertility", "ko": "정액 취급·웅돈 수정능력 점검",
        "zh": "检查精液处理与公猪繁殖力",
        "es": "Comprobar el manejo del semen y la fertilidad del verraco",
        "vi": "Kiểm tra thao tác xử lý tinh và khả năng thụ tinh của đực giống",
        "th": "ตรวจสอบการจัดการน้ำเชื้อและความสมบูรณ์พันธุ์ของพ่อพันธุ์",
        "pt": "Verificar o manuseio do sêmen e a fertilidade do cachaço"},
    "check_semen_quality_and_storage": {
        "en": "Check semen quality and storage", "ko": "정액 품질·보관 점검",
        "zh": "检查精液品质与保存", "es": "Comprobar la calidad y conservación del semen",
        "vi": "Kiểm tra chất lượng và bảo quản tinh dịch", "th": "ตรวจสอบคุณภาพและการเก็บรักษาน้ำเชื้อ",
        "pt": "Verificar a qualidade e o armazenamento do sêmen"},
    "check_sow_parity_and_gestation_length": {
        "en": "Check sow parity profile and gestation length", "ko": "모돈 산차 분포·임신기간 점검",
        "zh": "检查母猪胎次结构与妊娠期长度",
        "es": "Comprobar la estructura de partos y la duración de la gestación",
        "vi": "Kiểm tra cơ cấu lứa đẻ và thời gian mang thai",
        "th": "ตรวจสอบโครงสร้างลำดับครอกและระยะเวลาตั้งท้อง",
        "pt": "Verificar o perfil de ordem de parto e a duração da gestação"},
    "check_water_and_feeder_access": {
        "en": "Check water and feeder access", "ko": "급수·급이 접근성 점검",
        "zh": "检查饮水与采食位可及性", "es": "Comprobar el acceso a agua y comederos",
        "vi": "Kiểm tra khả năng tiếp cận nước uống và máng ăn",
        "th": "ตรวจสอบการเข้าถึงน้ำและรางอาหาร",
        "pt": "Verificar o acesso à água e aos comedouros"},
    "complete_sow_inventory_entry_via_onboarding": {
        "en": "Complete sow inventory entry via onboarding", "ko": "온보딩으로 모돈 재고 입력 완료",
        "zh": "通过引导流程完成母猪存栏录入",
        "es": "Completar el inventario de cerdas mediante la configuración inicial",
        "vi": "Hoàn tất nhập đàn nái qua bước khởi tạo",
        "th": "กรอกข้อมูลจำนวนแม่สุกรให้ครบผ่านขั้นตอนเริ่มต้นใช้งาน",
        "pt": "Concluir o inventário de matrizes pela configuração inicial"},
    "complete_weaning_data_entry_for_current_year": {
        "en": "Complete weaning data entry for the current year", "ko": "당해 연도 이유 데이터 입력 완료",
        "zh": "补全本年度断奶数据录入", "es": "Completar el registro de destetes del año en curso",
        "vi": "Hoàn tất nhập dữ liệu cai sữa của năm nay",
        "th": "กรอกข้อมูลการหย่านมของปีนี้ให้ครบ",
        "pt": "Concluir o registro de desmames do ano corrente"},
    "consult_veterinarian_for_disease_screening": {
        "en": "Consult a veterinarian for disease screening", "ko": "수의사 상담 통한 질병 검사",
        "zh": "咨询兽医进行疫病筛查", "es": "Consultar al veterinario para cribado de enfermedades",
        "vi": "Tham vấn bác sĩ thú y để tầm soát bệnh",
        "th": "ปรึกษาสัตวแพทย์เพื่อตรวจคัดกรองโรค",
        "pt": "Consultar o veterinário para triagem de doenças"},
    "consult_veterinarian_for_finishing_mortality": {
        "en": "Consult vet for finishing mortality", "ko": "비육 폐사 수의사 상담",
        "zh": "就育肥死亡问题咨询兽医", "es": "Consultar al veterinario por la mortalidad en engorde",
        "vi": "Tham vấn thú y về tỷ lệ chết ở giai đoạn vỗ béo",
        "th": "ปรึกษาสัตวแพทย์เรื่องการตายในระยะขุน",
        "pt": "Consultar o veterinário sobre a mortalidade na terminação"},
    "consult_veterinarian_for_perinatal_loss": {
        "en": "Consult vet for perinatal loss", "ko": "주산기 손실 수의사 상담",
        "zh": "就围产期损失咨询兽医", "es": "Consultar al veterinario por pérdidas perinatales",
        "vi": "Tham vấn thú y về tổn thất quanh thời điểm đẻ",
        "th": "ปรึกษาสัตวแพทย์เรื่องการสูญเสียช่วงรอบคลอด",
        "pt": "Consultar o veterinário sobre perdas perinatais"},
    "consult_veterinarian_for_reproductive_disease_screening": {
        "en": "Consult vet for reproductive disease screening", "ko": "번식 질환 수의사 상담",
        "zh": "就繁殖性疾病筛查咨询兽医",
        "es": "Consultar al veterinario para cribado de enfermedades reproductivas",
        "vi": "Tham vấn thú y để tầm soát bệnh sinh sản",
        "th": "ปรึกษาสัตวแพทย์เพื่อตรวจคัดกรองโรคระบบสืบพันธุ์",
        "pt": "Consultar o veterinário para triagem de doenças reprodutivas"},
    "consult_veterinarian_for_sow_mortality": {
        "en": "Consult vet for sow mortality", "ko": "모돈 폐사 수의사 상담",
        "zh": "就母猪死亡问题咨询兽医", "es": "Consultar al veterinario por la mortalidad de cerdas",
        "vi": "Tham vấn thú y về tỷ lệ nái chết", "th": "ปรึกษาสัตวแพทย์เรื่องการตายของแม่สุกร",
        "pt": "Consultar o veterinário sobre a mortalidade de matrizes"},
    "implement_biosecurity_level_3_protocol": {
        "en": "Implement biosecurity level 3 protocol", "ko": "차단방역 레벨 3 프로토콜 시행",
        "zh": "执行三级生物安全方案", "es": "Implantar el protocolo de bioseguridad de nivel 3",
        "vi": "Áp dụng quy trình an toàn sinh học cấp 3",
        "th": "ใช้มาตรการความปลอดภัยทางชีวภาพระดับ 3",
        "pt": "Implantar o protocolo de biosseguridade nível 3"},
    "improve_colostrum_and_cross_fostering": {
        "en": "Improve colostrum intake and cross-fostering", "ko": "초유 급여·양자 개선",
        "zh": "改善初乳摄入与寄养", "es": "Mejorar la ingesta de calostro y las adopciones",
        "vi": "Cải thiện việc bú sữa đầu và ghép bầy", "th": "ปรับปรุงการได้รับนมน้ำเหลืองและการฝากเลี้ยง",
        "pt": "Melhorar a ingestão de colostro e as adoções"},
    "improve_colostrum_intake_and_cross_fostering": {
        "en": "Improve colostrum intake and cross-fostering", "ko": "초유 섭취·양자(포유) 관리 개선",
        "zh": "改善初乳摄入与寄养管理", "es": "Mejorar la ingesta de calostro y el manejo de adopciones",
        "vi": "Cải thiện lượng sữa đầu bú được và quản lý ghép bầy",
        "th": "ปรับปรุงการกินนมน้ำเหลืองและการจัดการฝากเลี้ยง",
        "pt": "Melhorar a ingestão de colostro e o manejo de adoções"},
    "improve_creep_area_and_heat_lamp": {
        "en": "Improve creep area and heat lamp", "ko": "보온구역·보온등 개선",
        "zh": "改善仔猪保温区与保温灯", "es": "Mejorar el nido de lechones y la lámpara de calor",
        "vi": "Cải thiện khu úm heo con và đèn sưởi",
        "th": "ปรับปรุงพื้นที่กกลูกสุกรและโคมไฟกก",
        "pt": "Melhorar o escamoteador e a lâmpada de aquecimento"},
    "improve_lactation_feed_and_creep": {
        "en": "Improve lactation feed and creep management", "ko": "포유사료·보조사료(크립) 관리 개선",
        "zh": "改善哺乳料与教槽料管理",
        "es": "Mejorar el pienso de lactación y el manejo del pienso de iniciación",
        "vi": "Cải thiện thức ăn nuôi con và quản lý thức ăn tập ăn",
        "th": "ปรับปรุงอาหารระยะเลี้ยงลูกและการจัดการอาหารเสริมลูกสุกร",
        "pt": "Melhorar a ração de lactação e o manejo da ração pré-inicial"},
    "improve_p1_lactation_feed_and_bcs": {
        "en": "Improve P1 lactation feed and body condition", "ko": "1산차 포유사료·체형 개선",
        "zh": "改善头胎母猪哺乳料与体况",
        "es": "Mejorar el pienso de lactación y la condición corporal en primerizas",
        "vi": "Cải thiện thức ăn nuôi con và thể trạng nái lứa 1",
        "th": "ปรับปรุงอาหารระยะเลี้ยงลูกและสภาพร่างกายของแม่ครอกแรก",
        "pt": "Melhorar a ração de lactação e a condição corporal das primíparas"},
    "improve_post_weaning_heat_detection": {
        "en": "Improve post-weaning heat detection", "ko": "이유 후 발정 탐지 개선",
        "zh": "改善断奶后发情鉴定", "es": "Mejorar la detección de celo tras el destete",
        "vi": "Cải thiện phát hiện động dục sau cai sữa", "th": "ปรับปรุงการจับสัดหลังหย่านม",
        "pt": "Melhorar a detecção de cio pós-desmame"},
    "improve_psy_and_finishing_survival": {
        "en": "Improve PSY and finishing survival", "ko": "PSY·비육 생존율 개선",
        "zh": "改善PSY与育肥存活率", "es": "Mejorar el PSY y la supervivencia en engorde",
        "vi": "Cải thiện PSY và tỷ lệ sống giai đoạn vỗ béo",
        "th": "ปรับปรุง PSY และอัตรารอดในระยะขุน",
        "pt": "Melhorar o PSY e a sobrevivência na terminação"},
    "improve_summer_cooling_and_ventilation": {
        "en": "Improve summer cooling and ventilation", "ko": "여름 냉방·환기 개선",
        "zh": "改善夏季降温与通风", "es": "Mejorar la refrigeración y ventilación estivales",
        "vi": "Cải thiện làm mát và thông gió mùa hè",
        "th": "ปรับปรุงการทำความเย็นและการระบายอากาศในหน้าร้อน",
        "pt": "Melhorar o resfriamento e a ventilação no verão"},
    "improve_transition_feed_intake": {
        "en": "Improve transition feed intake", "ko": "전환기 사료 섭취 개선",
        "zh": "改善过渡期采食量", "es": "Mejorar el consumo de pienso en la transición",
        "vi": "Cải thiện lượng ăn giai đoạn chuyển tiếp", "th": "ปรับปรุงการกินอาหารช่วงเปลี่ยนผ่าน",
        "pt": "Melhorar o consumo de ração na transição"},
    "increase_biosecurity_monitoring": {
        "en": "Increase biosecurity monitoring", "ko": "차단방역 모니터링 강화",
        "zh": "加强生物安全监测", "es": "Reforzar la vigilancia de bioseguridad",
        "vi": "Tăng cường giám sát an toàn sinh học",
        "th": "เพิ่มการเฝ้าระวังด้านความปลอดภัยทางชีวภาพ",
        "pt": "Reforçar o monitoramento de biosseguridade"},
    "interpret_weekly_kpis_with_batch_cycle_in_mind": {
        "en": "Interpret weekly KPIs with the batch cycle in mind", "ko": "주간 KPI를 배치 주기 감안해 해석",
        "zh": "结合批次周期解读周度KPI",
        "es": "Interpretar los KPI semanales teniendo en cuenta el ciclo de lotes",
        "vi": "Diễn giải KPI hằng tuần có tính đến chu kỳ lô",
        "th": "ตีความ KPI รายสัปดาห์โดยคำนึงถึงรอบการผลิตแบบรุ่น",
        "pt": "Interpretar os KPIs semanais considerando o ciclo de lotes"},
    "investigate_finishing_health_and_environment": {
        "en": "Investigate finishing health and environment", "ko": "비육 건강·환경 조사",
        "zh": "调查育肥阶段健康与环境", "es": "Investigar la sanidad y el ambiente en engorde",
        "vi": "Điều tra sức khỏe và môi trường giai đoạn vỗ béo",
        "th": "ตรวจสอบสุขภาพและสภาพแวดล้อมในระยะขุน",
        "pt": "Investigar a sanidade e o ambiente na terminação"},
    "isolate_affected_animals_immediately": {
        "en": "Isolate affected animals immediately", "ko": "감염 의심 개체 즉시 격리",
        "zh": "立即隔离发病个体", "es": "Aislar de inmediato los animales afectados",
        "vi": "Cách ly ngay những con bị ảnh hưởng", "th": "แยกสัตว์ที่ได้รับผลกระทบทันที",
        "pt": "Isolar imediatamente os animais afetados"},
    "notify_veterinary_authority": {
        "en": "Notify the veterinary authority", "ko": "방역 당국 신고",
        "zh": "向兽医主管部门报告", "es": "Notificar a la autoridad veterinaria",
        "vi": "Thông báo cho cơ quan thú y", "th": "แจ้งหน่วยงานปศุสัตว์",
        "pt": "Notificar a autoridade veterinária"},
    "plan_gilt_introduction_cadence": {
        "en": "Plan gilt introduction cadence", "ko": "후보돈 도입 주기 계획",
        "zh": "规划后备母猪引入节奏", "es": "Planificar la cadencia de entrada de cerdas de reposición",
        "vi": "Lập kế hoạch nhịp nhập nái hậu bị", "th": "วางแผนรอบการนำสุกรสาวทดแทนเข้าฝูง",
        "pt": "Planejar a cadência de entrada de leitoas"},
    "reduce_early_culling_below_breakeven_parity": {
        "en": "Reduce culling below break-even parity (3.5)", "ko": "손익분기(3.5산) 미만 조기도태 감소",
        "zh": "减少低于盈亏平衡胎次(3.5胎)的过早淘汰",
        "es": "Reducir las eliminaciones por debajo del parto de equilibrio (3,5)",
        "vi": "Giảm loại thải trước lứa hòa vốn (3,5)",
        "th": "ลดการคัดทิ้งก่อนถึงลำดับครอกคุ้มทุน (3.5)",
        "pt": "Reduzir descartes abaixo da ordem de parto de equilíbrio (3,5)"},
    "reduce_npd_to_shorten_cycle_and_improve_psy": {
        "en": "Reduce NPD to shorten inter-litter interval", "ko": "NPD 감소로 분만간격 단축",
        "zh": "减少非生产天数以缩短产仔间隔",
        "es": "Reducir los DNP para acortar el intervalo entre partos",
        "vi": "Giảm ngày không sản xuất để rút ngắn khoảng cách lứa đẻ",
        "th": "ลดวันไม่ให้ผลผลิตเพื่อย่นช่วงห่างระหว่างครอก",
        "pt": "Reduzir os DNP para encurtar o intervalo entre partos"},
    "reduce_pregnancy_accidents_to_recover_loss": {
        "en": "Reduce pregnancy accidents to recover this loss", "ko": "임신사고 감소로 손실 회복",
        "zh": "减少妊娠事故以挽回该损失",
        "es": "Reducir las incidencias de gestación para recuperar esta pérdida",
        "vi": "Giảm sự cố mang thai để bù lại thiệt hại này",
        "th": "ลดอุบัติการณ์ระหว่างตั้งท้องเพื่อกู้คืนความสูญเสียนี้",
        "pt": "Reduzir acidentes de gestação para recuperar esta perda"},
    "reduce_preweaning_mortality_to_recover_loss": {
        "en": "Reduce pre-weaning mortality to recover this loss", "ko": "포유폐사 감소로 손실 회복",
        "zh": "降低断奶前死亡率以挽回该损失",
        "es": "Reducir la mortalidad predestete para recuperar esta pérdida",
        "vi": "Giảm tỷ lệ chết trước cai sữa để bù lại thiệt hại này",
        "th": "ลดการตายก่อนหย่านมเพื่อกู้คืนความสูญเสียนี้",
        "pt": "Reduzir a mortalidade pré-desmame para recuperar esta perda"},
    "reduce_weaning_to_service_interval_to_recover_loss": {
        "en": "Reduce weaning-to-service interval to recover this loss",
        "ko": "이유~교배 간격 단축으로 손실 회복",
        "zh": "缩短断奶至配种间隔以挽回该损失",
        "es": "Acortar el intervalo destete-cubrición para recuperar esta pérdida",
        "vi": "Rút ngắn khoảng cách cai sữa đến phối giống để bù lại thiệt hại này",
        "th": "ย่นช่วงหย่านมถึงผสมพันธุ์เพื่อกู้คืนความสูญเสียนี้",
        "pt": "Encurtar o intervalo desmame-cobertura para recuperar esta perda"},
    "report_to_national_veterinary_authority": {
        "en": "Report to the national veterinary authority", "ko": "국가 방역 당국 신고",
        "zh": "向国家兽医主管部门报告", "es": "Informar a la autoridad veterinaria nacional",
        "vi": "Báo cáo cho cơ quan thú y quốc gia", "th": "รายงานต่อหน่วยงานปศุสัตว์ระดับประเทศ",
        "pt": "Comunicar à autoridade veterinária nacional"},
    "review_boar_usage_and_libido": {
        "en": "Review boar usage rotation and libido", "ko": "웅돈 사용 로테이션·성욕 검토",
        "zh": "检查公猪使用轮换与性欲", "es": "Revisar la rotación de uso del verraco y su libido",
        "vi": "Xem lại luân phiên sử dụng và tính hăng của đực giống",
        "th": "ทบทวนการหมุนเวียนใช้พ่อพันธุ์และความต้องการผสมพันธุ์",
        "pt": "Revisar o rodízio de uso do cachaço e a libido"},
    "review_crushing_prevention_and_creep_management": {
        "en": "Review crushing prevention and creep management",
        "ko": "압사 예방·자돈 보온구역(크립) 관리 점검",
        "zh": "检查防压死措施与仔猪保温区管理",
        "es": "Revisar la prevención de aplastamientos y el manejo del nido",
        "vi": "Xem lại biện pháp chống đè chết và quản lý khu úm heo con",
        "th": "ทบทวนการป้องกันแม่ทับและการจัดการพื้นที่กกลูกสุกร",
        "pt": "Revisar a prevenção de esmagamento e o manejo do escamoteador"},
    "review_culling_policy_and_reasons": {
        "en": "Review culling policy and reasons", "ko": "도태 기준·사유 검토",
        "zh": "检查淘汰标准与原因", "es": "Revisar la política y las causas de eliminación",
        "vi": "Xem lại chính sách và lý do loại thải", "th": "ทบทวนเกณฑ์และเหตุผลการคัดทิ้ง",
        "pt": "Revisar a política e os motivos de descarte"},
    "review_early_weaning_protocol": {
        "en": "Review early-weaning protocol", "ko": "조기이유 프로토콜 검토",
        "zh": "检查早期断奶方案", "es": "Revisar el protocolo de destete precoz",
        "vi": "Xem lại quy trình cai sữa sớm", "th": "ทบทวนแนวปฏิบัติการหย่านมเร็ว",
        "pt": "Revisar o protocolo de desmame precoce"},
    "review_farrowing_crate_and_supervision": {
        "en": "Review farrowing crate setup and supervision", "ko": "분만틀 설치·입회 점검",
        "zh": "检查分娩栏设置与接产看护",
        "es": "Revisar la instalación de las jaulas de parto y la supervisión",
        "vi": "Xem lại bố trí chuồng đẻ và việc trực đỡ đẻ",
        "th": "ทบทวนการจัดซองคลอดและการเฝ้าคลอด",
        "pt": "Revisar a instalação das celas parideiras e a supervisão"},
    "review_farrowing_supervision": {
        "en": "Increase farrowing attendance/supervision", "ko": "분만 입회·관리 강화",
        "zh": "加强分娩看护与接产", "es": "Aumentar la asistencia y supervisión del parto",
        "vi": "Tăng cường trực và hỗ trợ lúc nái đẻ", "th": "เพิ่มการเฝ้าคลอดและช่วยคลอด",
        "pt": "Aumentar o acompanhamento e a supervisão do parto"},
    "review_finishing_diet_and_stocking_density": {
        "en": "Review finishing diet and stocking density", "ko": "비육 사료·사육밀도 검토",
        "zh": "检查育肥日粮与饲养密度", "es": "Revisar la dieta de engorde y la densidad de alojamiento",
        "vi": "Xem lại khẩu phần vỗ béo và mật độ nuôi",
        "th": "ทบทวนสูตรอาหารระยะขุนและความหนาแน่นการเลี้ยง",
        "pt": "Revisar a dieta de terminação e a densidade de alojamento"},
    "review_gestation_biosecurity_and_vaccination": {
        "en": "Review gestation biosecurity and vaccination", "ko": "임신사 방역·백신 프로그램 점검",
        "zh": "检查妊娠舍生物安全与免疫程序",
        "es": "Revisar la bioseguridad y vacunación en gestación",
        "vi": "Xem lại an toàn sinh học và tiêm phòng khu nái chửa",
        "th": "ทบทวนความปลอดภัยทางชีวภาพและโปรแกรมวัคซีนในโรงเรือนอุ้มท้อง",
        "pt": "Revisar a biosseguridade e a vacinação na gestação"},
    "review_gilt_acclimation_and_vaccination": {
        "en": "Review gilt acclimation and vaccination", "ko": "후보돈 순화·백신 검토",
        "zh": "检查后备母猪驯化与免疫",
        "es": "Revisar la aclimatación y vacunación de cerdas de reposición",
        "vi": "Xem lại việc thuần hóa và tiêm phòng nái hậu bị",
        "th": "ทบทวนการปรับสภาพและการทำวัคซีนสุกรสาวทดแทน",
        "pt": "Revisar a aclimatação e a vacinação de leitoas"},
    "review_gilt_development_and_sow_nutrition": {
        "en": "Review gilt development and sow nutrition", "ko": "후보돈 육성·모돈 영양 검토",
        "zh": "检查后备母猪培育与母猪营养",
        "es": "Revisar el desarrollo de la reposición y la nutrición de las cerdas",
        "vi": "Xem lại quá trình nuôi hậu bị và dinh dưỡng nái",
        "th": "ทบทวนการเลี้ยงสุกรสาวทดแทนและโภชนาการแม่สุกร",
        "pt": "Revisar o desenvolvimento das leitoas e a nutrição das matrizes"},
    "review_gilt_intake_plan": {
        "en": "Review gilt intake plan", "ko": "후보돈 도입 계획 검토",
        "zh": "检查后备母猪引入计划", "es": "Revisar el plan de entrada de cerdas de reposición",
        "vi": "Xem lại kế hoạch nhập nái hậu bị", "th": "ทบทวนแผนการนำสุกรสาวทดแทนเข้าฝูง",
        "pt": "Revisar o plano de entrada de leitoas"},
    "review_gilt_replacement_plan": {
        "en": "Review gilt replacement plan", "ko": "후보돈 보충 계획 검토",
        "zh": "检查后备母猪补充计划", "es": "Revisar el plan de reposición de cerdas",
        "vi": "Xem lại kế hoạch bổ sung nái hậu bị", "th": "ทบทวนแผนทดแทนแม่สุกรด้วยสุกรสาว",
        "pt": "Revisar o plano de reposição de matrizes"},
    "review_group_health": {
        "en": "Review group health records", "ko": "그룹 건강 기록 검토",
        "zh": "检查群体健康记录", "es": "Revisar los registros sanitarios del lote",
        "vi": "Xem lại hồ sơ sức khỏe của nhóm", "th": "ทบทวนบันทึกสุขภาพของกลุ่มสุกร",
        "pt": "Revisar os registros sanitários do lote"},
    "review_heat_detection_accuracy": {
        "en": "Review heat detection accuracy", "ko": "발정 탐지 정확도 점검",
        "zh": "检查发情鉴定准确性", "es": "Revisar la precisión de la detección de celo",
        "vi": "Xem lại độ chính xác của việc phát hiện động dục", "th": "ทบทวนความแม่นยำในการจับสัด",
        "pt": "Revisar a precisão da detecção de cio"},
    "review_heat_detection_frequency": {
        "en": "Review heat detection frequency", "ko": "발정 탐지 빈도 검토",
        "zh": "检查发情鉴定频次", "es": "Revisar la frecuencia de detección de celo",
        "vi": "Xem lại tần suất kiểm tra động dục", "th": "ทบทวนความถี่ในการจับสัด",
        "pt": "Revisar a frequência da detecção de cio"},
    "review_heat_stress_and_body_condition": {
        "en": "Review heat stress and body condition", "ko": "고온스트레스·체형 관리 검토",
        "zh": "检查热应激与体况管理", "es": "Revisar el estrés térmico y la condición corporal",
        "vi": "Xem lại stress nhiệt và thể trạng",
        "th": "ทบทวนความเครียดจากความร้อนและสภาพร่างกาย",
        "pt": "Revisar o estresse térmico e a condição corporal"},
    "review_involuntary_culling_drivers": {
        "en": "Review involuntary-culling drivers", "ko": "비자발 도태 원인 검토",
        "zh": "检查被动淘汰的主要原因", "es": "Revisar las causas de eliminación involuntaria",
        "vi": "Xem lại nguyên nhân loại thải bắt buộc", "th": "ทบทวนสาเหตุของการคัดทิ้งโดยจำเป็น",
        "pt": "Revisar as causas de descarte involuntário"},
    "review_lactation_feed_intake": {
        "en": "Review lactation feed intake", "ko": "포유기 사료 섭취 점검",
        "zh": "检查哺乳期采食量", "es": "Revisar el consumo de pienso en lactación",
        "vi": "Xem lại lượng ăn của nái nuôi con", "th": "ทบทวนการกินอาหารในระยะเลี้ยงลูก",
        "pt": "Revisar o consumo de ração na lactação"},
    "review_parity_structure_and_replacement": {
        "en": "Review parity structure and replacement", "ko": "산차 구조·보충 검토",
        "zh": "检查胎次结构与更新补充", "es": "Revisar la estructura de partos y la reposición",
        "vi": "Xem lại cơ cấu lứa đẻ và việc thay đàn",
        "th": "ทบทวนโครงสร้างลำดับครอกและการทดแทนฝูง",
        "pt": "Revisar a estrutura de ordem de parto e a reposição"},
    "review_sow_milk_yield": {
        "en": "Review sow milk yield/udder health", "ko": "모돈 비유량·유방 건강 점검",
        "zh": "检查母猪泌乳量与乳房健康", "es": "Revisar la producción láctea y la salud de la ubre",
        "vi": "Xem lại sản lượng sữa và sức khỏe bầu vú của nái",
        "th": "ทบทวนปริมาณน้ำนมและสุขภาพเต้านมของแม่สุกร",
        "pt": "Revisar a produção de leite e a saúde da glândula mamária"},
    "review_sow_nutrition_and_genetic_merit": {
        "en": "Review sow nutrition and genetic merit", "ko": "모돈 영양 및 유전 능력 검토",
        "zh": "检查母猪营养与遗传性能", "es": "Revisar la nutrición y el mérito genético de las cerdas",
        "vi": "Xem lại dinh dưỡng và tiềm năng di truyền của nái",
        "th": "ทบทวนโภชนาการและพันธุกรรมของแม่สุกร",
        "pt": "Revisar a nutrição e o mérito genético das matrizes"},
    "review_sow_throughput_and_npd": {
        "en": "Review sow throughput and NPD", "ko": "모돈 회전율·NPD 검토",
        "zh": "检查母猪周转率与非生产天数", "es": "Revisar la productividad de la cerda y los DNP",
        "vi": "Xem lại vòng quay đàn nái và ngày không sản xuất",
        "th": "ทบทวนรอบการผลิตของแม่สุกรและวันไม่ให้ผลผลิต",
        "pt": "Revisar o giro do plantel de matrizes e os DNP"},
    "review_summer_feed_intake_and_boar_exposure": {
        "en": "Review summer feed intake and boar exposure", "ko": "여름 사료섭취·웅돈접촉 검토",
        "zh": "检查夏季采食量与公猪诱情",
        "es": "Revisar el consumo estival de pienso y la exposición al verraco",
        "vi": "Xem lại lượng ăn mùa hè và việc cho tiếp xúc đực giống",
        "th": "ทบทวนการกินอาหารหน้าร้อนและการใช้พ่อพันธุ์กระตุ้นสัด",
        "pt": "Revisar o consumo de ração no verão e a exposição ao cachaço"},
    "review_throughput_and_mortality": {
        "en": "Review throughput and mortality", "ko": "회전율·폐사 검토",
        "zh": "检查周转率与死亡情况", "es": "Revisar la productividad y la mortalidad",
        "vi": "Xem lại vòng quay đàn và tỷ lệ chết", "th": "ทบทวนรอบการผลิตและอัตราการตาย",
        "pt": "Revisar o giro do plantel e a mortalidade"},
    "screen_for_abortive_pathogens": {
        "en": "Screen for abortive pathogens", "ko": "유산성 병원체 검사",
        "zh": "筛查流产性病原", "es": "Realizar cribado de patógenos abortivos",
        "vi": "Xét nghiệm tầm soát mầm bệnh gây sảy thai", "th": "ตรวจคัดกรองเชื้อก่อโรคที่ทำให้แท้ง",
        "pt": "Realizar triagem de patógenos abortivos"},
    "shorten_p1_wean_to_service_interval": {
        "en": "Shorten P1 wean-to-service interval", "ko": "1산차 이유~교배 간격 단축",
        "zh": "缩短头胎母猪断奶至配种间隔",
        "es": "Acortar el intervalo destete-cubrición en primerizas",
        "vi": "Rút ngắn khoảng cách cai sữa đến phối giống ở nái lứa 1",
        "th": "ย่นช่วงหย่านมถึงผสมพันธุ์ของแม่ครอกแรก",
        "pt": "Encurtar o intervalo desmame-cobertura das primíparas"},
    "verify_animal_origin_and_import_health_certificates": {
        "en": "Verify animal origin and import health certificates", "ko": "개체 원산지·수입 검역증명서 확인",
        "zh": "核实动物来源与进口检疫证明",
        "es": "Verificar el origen de los animales y los certificados sanitarios de importación",
        "vi": "Xác minh nguồn gốc con giống và giấy chứng nhận kiểm dịch nhập khẩu",
        "th": "ตรวจสอบแหล่งที่มาของสัตว์และใบรับรองสุขภาพนำเข้า",
        "pt": "Verificar a origem dos animais e os certificados sanitários de importação"},
    "verify_boar_exposure_protocol": {
        "en": "Verify boar exposure protocol", "ko": "웅돈 접촉 프로토콜 점검",
        "zh": "检查公猪诱情操作规程", "es": "Verificar el protocolo de exposición al verraco",
        "vi": "Kiểm tra quy trình cho tiếp xúc đực giống",
        "th": "ตรวจสอบแนวปฏิบัติการใช้พ่อพันธุ์กระตุ้นสัด",
        "pt": "Verificar o protocolo de exposição ao cachaço"},
}

# ── 렌더러 고정 문구 ──────────────────────────────────────────────────────────
UI_LABELS: dict[str, dict[str, str]] = {
    "causes": {
        "en": "Causes", "ko": "원인", "zh": "原因", "es": "Causas",
        "vi": "Nguyên nhân", "th": "สาเหตุ", "pt": "Causas"},
    "actions": {
        "en": "Actions", "ko": "조치", "zh": "建议措施", "es": "Acciones",
        "vi": "Hành động", "th": "แนวทางแก้ไข", "pt": "Ações"},
    "loss": {
        "en": "Loss", "ko": "손실", "zh": "损失", "es": "Pérdida",
        "vi": "Thiệt hại", "th": "ความสูญเสีย", "pt": "Perda"},
    "estimated": {
        "en": "est.", "ko": "추정", "zh": "估算", "es": "estim.",
        "vi": "ước tính", "th": "ประมาณการ", "pt": "estim."},
    "target": {
        "en": "target", "ko": "목표", "zh": "目标", "es": "objetivo",
        "vi": "mục tiêu", "th": "เป้าหมาย", "pt": "meta"},
    "all_normal": {
        "en": "All KPIs are within normal range.", "ko": "모든 KPI가 정상 범위입니다.",
        "zh": "所有KPI均在正常范围内。", "es": "Todos los KPI están dentro del rango normal.",
        "vi": "Tất cả các chỉ số KPI đều trong ngưỡng bình thường.",
        "th": "ตัวชี้วัดทั้งหมดอยู่ในเกณฑ์ปกติ",
        "pt": "Todos os KPIs estão dentro da faixa normal."},
    # 심각도 라벨 — ★ 글리프를 넣지 않는다.
    # 이 문자열은 챗 응답 본문으로 그대로 나간다. 예전에는 "🔴 Critical" / "⚠ 경고" / "✓" 처럼
    # 이모지가 섞여 있었는데, 서버가 만든 텍스트라 클라이언트가 색·크기·정렬을 잡을 수
    # 없고 스크린리더가 글리프를 읽는다. 등급은 StructuredResult.severity 필드로도
    # 내려가므로, 표시 강조는 그쪽을 보고 클라이언트가 한다.
    # ★ ok/info 의 현지어는 2026-09-09 신규 — 나머지 6키와 달리 원어민 검수 미이행(검토 대상).
    "severity_ok": {
        "en": "OK", "ko": "정상", "zh": "正常", "es": "Normal",
        "vi": "Bình thường", "th": "ปกติ", "pt": "Normal"},
    "severity_info": {
        "en": "Info", "ko": "참고", "zh": "提示", "es": "Info",
        "vi": "Thông tin", "th": "ข้อมูล", "pt": "Info"},
    "severity_warning": {
        "en": "Warning", "ko": "경고", "zh": "警告", "es": "Aviso",
        "vi": "Cảnh báo", "th": "คำเตือน", "pt": "Alerta"},
    "severity_critical": {
        "en": "Critical", "ko": "위험", "zh": "严重", "es": "Crítico",
        "vi": "Nghiêm trọng", "th": "วิกฤต", "pt": "Crítico"},
}


# ── intent 분류 키워드 ────────────────────────────────────────────────────────
# 질문(소문자)에 부분일치하면 해당 intent. 언어를 가리지 않고 한 리스트에 모아두므로
# 사용자의 표시 언어와 질문 언어가 달라도 잡힌다.
# **순서가 곧 우선순위**다 — 가장 포괄적인 "dashboard"를 맨 뒤에 둔다.
# 여기 없는 언어로 물으면 intent가 안 잡혀 "unknown"이 되므로, 언어를 늘리면 여기도 채울 것.
INTENT_KEYWORDS: dict[str, list[str]] = {
    "psy": [
        "psy", "piglets per sow", "productivity",
        "생산성", "이유두수",
        "每头母猪", "断奶仔猪数", "生产力",
        "productividad", "lechones por cerda",
        "năng suất", "heo con cai sữa trên nái",
        "ผลิตภาพ", "ลูกหย่านมต่อแม่",
        "produtividade", "leitões por matriz",
    ],
    "npd": [
        "npd", "non-productive", "idle", "weaning interval",
        "비생산일", "이유 간격",
        "非生产天数", "断奶间隔",
        "días no productivos", "dnp", "intervalo destete",
        "ngày không sản xuất", "khoảng cách cai sữa",
        "วันไม่ให้ผลผลิต", "ช่วงหย่านม",
        "dias não produtivos", "intervalo desmame",
    ],
    "farrowing": [
        "farrowing rate", "farrowing", "conception",
        "분만율", "분만", "수태",
        "分娩率", "分娩", "受胎",
        "tasa de partos", "concepción",
        "tỷ lệ đẻ", "thụ thai",
        "อัตราการคลอด", "การคลอด", "ผสมติด",
        "taxa de parto", "concepção",
    ],
    "inventory": [
        "sow count", "inventory",
        "모돈 수", "재고",
        "母猪存栏", "存栏",
        "censo", "inventario", "número de cerdas",
        "tổng đàn nái", "số nái", "tồn đàn",
        "จำนวนแม่สุกร", "จำนวนคงเหลือ",
        "plantel", "inventário", "número de matrizes",
    ],
    # "fcr" → base tier에 fcr 룰이 없어 findings 0. Addon에서 활성화된다.
    "fcr": [
        "fcr", "feed conversion", "feed efficiency",
        "사료효율", "사료요구율",
        "料肉比", "饲料转化率", "饲料效率",
        "conversión alimenticia", "índice de conversión", "eficiencia alimentaria",
        "hệ số chuyển hóa thức ăn", "hiệu quả thức ăn",
        "อัตราแลกเนื้อ", "ประสิทธิภาพอาหาร",
        "conversão alimentar", "eficiência alimentar",
    ],
    # 포괄 질문("우리 농장 어때?") — 반드시 마지막.
    "dashboard": [
        "farm status", "overall", "summary", "dashboard", "kpi", "how is",
        "농장 상태", "상태", "전체", "요약", "현황",
        "农场状况", "猪场", "整体", "概况", "汇总", "状况",
        "estado de la granja", "estado", "resumen", "general",
        "tình hình", "tổng quan", "tóm tắt",
        "สถานะฟาร์ม", "ภาพรวม", "สรุป",
        "situação", "resumo", "geral",
    ],
}

# intent 표시명 — "OO 지표는 정상 범위" 문구에 끼워 넣는다.
INTENT_LABELS: dict[str, dict[str, str]] = {
    "psy": {
        "en": "PSY", "ko": "PSY(모돈당 연간 이유두수)", "zh": "PSY(每头母猪年断奶仔猪数)",
        "es": "PSY (lechones destetados por cerda y año)", "vi": "PSY (số heo cai sữa/nái/năm)",
        "th": "PSY (ลูกหย่านมต่อแม่ต่อปี)", "pt": "PSY (leitões desmamados por matriz/ano)"},
    "npd": {
        "en": "non-productive days", "ko": "비생산일(NPD)", "zh": "非生产天数",
        "es": "días no productivos", "vi": "ngày không sản xuất",
        "th": "วันไม่ให้ผลผลิต", "pt": "dias não produtivos"},
    "farrowing": {
        "en": "farrowing rate", "ko": "분만율", "zh": "分娩率",
        "es": "tasa de partos", "vi": "tỷ lệ đẻ",
        "th": "อัตราการคลอด", "pt": "taxa de parto"},
    "inventory": {
        "en": "sow inventory", "ko": "모돈 재고", "zh": "母猪存栏",
        "es": "censo de cerdas", "vi": "tổng đàn nái",
        "th": "จำนวนแม่สุกรคงเหลือ", "pt": "plantel de matrizes"},
    "fcr": {
        "en": "feed conversion", "ko": "사료요구율(FCR)", "zh": "料肉比",
        "es": "conversión alimenticia", "vi": "hệ số chuyển hóa thức ăn",
        "th": "อัตราแลกเนื้อ", "pt": "conversão alimentar"},
}

UI_LABELS.update({
    # 질문을 어떤 intent로도 분류하지 못했을 때. 답을 아예 안 주는 대신
    # "못 알아들었다"고 밝히고 농장 전체 요약으로 이어간다.
    "unknown_intent": {
        "en": "I could not match that question to a farm metric. "
              "I can answer about PSY, farrowing rate, non-productive days, sow inventory, "
              "and feed conversion. Here is the overall farm summary instead:",
        "ko": "질문을 농장 지표로 연결하지 못했습니다. "
              "PSY·분만율·비생산일·모돈 재고·사료요구율에 대해 답할 수 있습니다. "
              "대신 농장 전체 요약을 보여드립니다:",
        "zh": "无法将该问题对应到农场指标。"
              "我可以回答PSY、分娩率、非生产天数、母猪存栏和料肉比相关问题。"
              "以下为猪场整体概况：",
        "es": "No he podido asociar esa pregunta a un indicador de la granja. "
              "Puedo responder sobre PSY, tasa de partos, días no productivos, censo de cerdas "
              "y conversión alimenticia. En su lugar, este es el resumen general:",
        "vi": "Tôi không khớp được câu hỏi đó với chỉ số của trại. "
              "Tôi có thể trả lời về PSY, tỷ lệ đẻ, ngày không sản xuất, tổng đàn nái "
              "và hệ số chuyển hóa thức ăn. Dưới đây là tổng quan toàn trại:",
        "th": "ไม่สามารถจับคู่คำถามนี้กับตัวชี้วัดของฟาร์มได้ "
              "ระบบตอบได้เกี่ยวกับ PSY อัตราการคลอด วันไม่ให้ผลผลิต จำนวนแม่สุกร "
              "และอัตราแลกเนื้อ ด้านล่างคือภาพรวมของฟาร์ม:",
        "pt": "Não consegui associar essa pergunta a um indicador da granja. "
              "Posso responder sobre PSY, taxa de parto, dias não produtivos, plantel de matrizes "
              "e conversão alimentar. Segue o resumo geral da granja:",
    },
    # 특정 지표를 물었는데 그 지표 룰이 아무 문제도 못 찾은 경우.
    # 기존엔 "모든 KPI가 정상 범위입니다"로 뭉개져서 무엇을 물었는지 사라졌다.
    "intent_within_target": {
        "en": "{kpi}: no issues detected — currently within the target range.",
        "ko": "{kpi}: 특이사항 없음 — 현재 목표 범위입니다.",
        "zh": "{kpi}：未发现异常——当前处于目标范围内。",
        "es": "{kpi}: sin incidencias — actualmente dentro del rango objetivo.",
        "vi": "{kpi}: không phát hiện vấn đề — hiện trong ngưỡng mục tiêu.",
        "th": "{kpi}: ไม่พบปัญหา — ขณะนี้อยู่ในเกณฑ์เป้าหมาย",
        "pt": "{kpi}: sem ocorrências — atualmente dentro da faixa-alvo.",
    },
})
