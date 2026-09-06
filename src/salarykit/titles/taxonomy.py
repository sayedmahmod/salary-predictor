"""Kanonische Jobtitel-Taxonomie.

Jeder Eintrag ist eine Rolle mit

* ``code``     - stabiler Schluessel ``familie.rolle``
* ``label``    - Anzeigename (der ``normalized_job_title``)
* ``family``   - grobe Berufsfamilie
* ``aliases``  - Schreibweisen und Uebersetzungen, auf die gematcht wird
* ``isco08`` / ``soc2018`` / ``kldb2010`` - Bruecken zu den amtlichen
  Statistiken (Eurostat SES / BLS OEWS / BA Entgeltstatistik). Damit lassen
  sich Mikrodaten und amtliche Quantile ueber denselben Beruf verbinden.

Die Aliasliste ist bewusst grosszuegig: sie ist zugleich das Trainingsmaterial
fuer den Klassifikator in :mod:`salarykit.titles.model`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FAMILIES: dict[str, str] = {
    "software": "Softwareentwicklung",
    "data_ai": "Daten, Analytics & KI",
    "infrastructure": "Infrastruktur, Cloud & Betrieb",
    "security": "IT-Sicherheit",
    "quality": "Test & Qualitaetssicherung",
    "product": "Produkt & Projekt",
    "design": "Design & UX",
    "research": "Forschung & Wissenschaft",
    "it_support": "IT-Support & Administration",
    "sales": "Vertrieb",
    "marketing": "Marketing & Kommunikation",
    "customer": "Kundenservice & Success",
    "hr": "Personal",
    "finance": "Finanzen & Rechnungswesen",
    "legal": "Recht & Compliance",
    "operations": "Operations & Unternehmensorganisation",
    "supply_chain": "Logistik & Supply Chain",
    "consulting": "Beratung",
    "management": "Geschaeftsfuehrung & Bereichsleitung",
    "engineering_industrial": "Technik & Ingenieurwesen",
    "trades": "Handwerk, Produktion & Instandhaltung",
    "healthcare": "Gesundheit & Pflege",
    "education": "Bildung & Erziehung",
    "hospitality": "Gastronomie & Hotellerie",
    "retail": "Handel & Verkauf",
    "transport": "Transport & Fahrdienste",
    "admin": "Administration & Sekretariat",
    "media": "Medien & Content",
    "generic": "Unspezifische Sammeltitel",
    "other": "Sonstiges",
}


@dataclass(frozen=True)
class Role:
    code: str
    label: str
    family: str
    aliases: tuple[str, ...] = ()
    isco08: str | None = None
    soc2018: str | None = None
    kldb2010: str | None = None
    exclude: tuple[str, ...] = ()   # Aliase, die trotz Treffer nicht zaehlen

    @property
    def isco_major(self) -> str | None:
        return self.isco08[0] if self.isco08 else None


def _r(code, label, family, aliases, isco08=None, soc2018=None, kldb2010=None,
       exclude=()) -> Role:
    return Role(code, label, family, tuple(aliases), isco08, soc2018, kldb2010,
                tuple(exclude))


ROLES: list[Role] = [
    # ---------------- Softwareentwicklung -------------------------------
    _r("software.engineer", "Software Engineer", "software", [
        "software engineer", "software developer", "software development engineer",
        "softwareentwickler", "software entwickler", "entwickler", "developer",
        "programmer", "programmierer", "sde", "swe", "software engineering",
        "software engineering", "softwareentwicklung",
        "ingenieur logiciel", "developpeur", "sviluppatore software",
        "desarrollador de software", "software craftsperson", "coder",
        "application developer", "anwendungsentwickler", "member of technical staff",
        "software developer engineer", "polyglot engineer", "generalist engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.backend", "Backend Engineer", "software", [
        "backend engineer", "back end engineer", "back-end engineer",
        "backend developer", "back end developer", "backend software engineer",
        "server side engineer", "serverside developer", "api engineer",
        "backend entwickler", "developpeur backend", "software engineer backend",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.frontend", "Frontend Engineer", "software", [
        "frontend engineer", "front end engineer", "front-end engineer",
        "frontend developer", "front end developer", "ui engineer",
        "javascript developer", "react developer", "angular developer",
        "vue developer", "web developer", "webentwickler", "frontend entwickler",
        "developpeur frontend", "html developer", "webdeveloper",
    ], isco08="2513", soc2018="15-1254", kldb2010="43"),
    _r("software.fullstack", "Full Stack Engineer", "software", [
        "full stack engineer", "fullstack engineer", "full-stack engineer",
        "full stack developer", "fullstack developer", "full-stack developer",
        "full stack software engineer", "fullstack entwickler",
        "developpeur full stack", "full stack web developer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.mobile", "Mobile Engineer", "software", [
        "mobile engineer", "mobile developer", "ios engineer", "ios developer",
        "android engineer", "android developer", "react native developer",
        "flutter developer", "mobile app developer", "app entwickler",
        "swift developer", "kotlin developer", "mobile software engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.embedded", "Embedded Engineer", "software", [
        "embedded engineer", "embedded software engineer", "firmware engineer",
        "embedded developer", "embedded systems engineer", "rtos engineer",
        "entwickler embedded", "embedded entwickler", "firmware developer",
        "systems software engineer", "kernel engineer", "driver developer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.games", "Game Engineer", "software", [
        "game developer", "game engineer", "gameplay engineer", "game programmer",
        "graphics engineer", "engine programmer", "unity developer",
        "unreal developer", "spieleentwickler", "rendering engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.architect", "Software Architect", "software", [
        "software architect", "softwarearchitekt", "solution architect",
        "solutions architect", "technical architect", "application architect",
        "enterprise architect", "systems architect", "it architect",
        "lead architect", "architecte logiciel", "loesungsarchitekt",
        "principal architect", "domain architect", "integration architect",
    ], isco08="2511", soc2018="15-1299", kldb2010="43"),
    _r("software.mlops", "MLOps Engineer", "software", [
        "mlops engineer", "ml infrastructure engineer", "ml platform engineer",
        "ml ops", "machine learning operations engineer", "aiops engineer",
        "model deployment engineer", "llmops engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("software.platform", "Platform Engineer", "software", [
        "platform engineer", "developer experience engineer", "devex engineer",
        "internal tools engineer", "infrastructure software engineer",
        "developer productivity engineer", "build engineer", "tooling engineer",
        "plattform engineer", "developer platform engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),

    # ---------------- Daten, Analytics, KI ------------------------------
    _r("data.scientist", "Data Scientist", "data_ai", [
        "data scientist", "datenwissenschaftler", "decision scientist",
        "scientifique des donnees", "data science", "senior data science",
        "product data scientist", "applied data scientist", "cientifico de datos",
        "data scientist analytics", "statistical scientist", "data science",
    ], isco08="2120", soc2018="15-2051", kldb2010="43"),
    _r("data.engineer", "Data Engineer", "data_ai", [
        "data engineer", "dateningenieur", "big data engineer", "etl developer",
        "etl engineer", "data pipeline engineer", "ingenieur donnees",
        "data infrastructure engineer", "data platform engineer",
        "data warehouse engineer", "data developer", "datenbank entwickler",
        "data engineering", "dateningenieurwesen",
        "hadoop engineer", "spark engineer", "data ops engineer", "dataops engineer",
    ], isco08="2521", soc2018="15-1243", kldb2010="43"),
    _r("data.analyst", "Data Analyst", "data_ai", [
        "data analyst", "datenanalyst", "analyste de donnees", "insight analyst",
        "reporting analyst", "data analytics", "analytics analyst",
        "data quality analyst", "data operations analyst", "web analyst",
        "marketing analyst", "operations analyst", "people analytics analyst",
        "data management analyst", "analista de datos", "junior data analyst",
        "datenanalyse", "analytics",
    ], isco08="2120", soc2018="15-2051", kldb2010="43"),
    _r("data.bi", "BI Analyst / Developer", "data_ai", [
        "business intelligence analyst", "bi analyst", "business intelligence",
        "business intelligence developer", "bi developer", "power bi developer",
        "tableau developer", "looker developer", "bi engineer",
        "business intelligence engineer", "bi consultant", "bi specialist",
        "qlik developer", "reporting specialist", "business intelligence manager",
    ], isco08="2120", soc2018="15-2051", kldb2010="43"),
    _r("data.analytics_engineer", "Analytics Engineer", "data_ai", [
        "analytics engineer", "dbt developer", "analytics developer",
        "data modeler", "data modelling engineer", "semantic layer engineer",
    ], isco08="2521", soc2018="15-1243", kldb2010="43"),
    _r("data.ml_engineer", "Machine Learning Engineer", "data_ai", [
        "machine learning engineer", "ml engineer", "ai engineer",
        "artificial intelligence engineer", "deep learning engineer",
        "ai developer", "ki entwickler", "machine learning developer",
        "nlp engineer", "computer vision engineer", "llm engineer",
        "genai engineer", "generative ai engineer", "ai software engineer",
        "machine learning", "maschinelles lernen", "kuenstliche intelligenz",
        "ingenieur machine learning", "ml software engineer", "ai/ml engineer",
        "forward deployed engineer", "applied ai engineer",
    ], isco08="2512", soc2018="15-1252", kldb2010="43"),
    _r("data.ml_scientist", "Machine Learning Scientist", "data_ai", [
        "machine learning scientist", "ml scientist", "applied scientist",
        "research scientist machine learning", "ai scientist",
        "machine learning researcher", "ai researcher", "ml researcher",
        "deep learning researcher", "applied research scientist",
        "member of technical staff research",
    ], isco08="2120", soc2018="15-1221", kldb2010="43"),
    _r("data.architect", "Data Architect", "data_ai", [
        "data architect", "datenarchitekt", "ai architect", "analytics architect",
        "data analytics architect", "big data architect", "information architect",
        "enterprise data architect", "data platform architect",
    ], isco08="2521", soc2018="15-1243", kldb2010="43"),
    _r("data.dba", "Database Administrator", "data_ai", [
        "database administrator", "dba", "datenbankadministrator",
        "sql server dba", "oracle dba", "database engineer", "datenbankbetreuer",
    ], isco08="2521", soc2018="15-1242", kldb2010="43"),
    _r("data.governance", "Data Governance Specialist", "data_ai", [
        "data governance", "data governance analyst", "data governance manager",
        "data steward", "data quality manager", "master data specialist",
        "stammdatenmanagement", "data management specialist", "data management",
        "metadata manager", "datenschutz datenmanagement", "datenmanagement",
        "data manager", "data lead", "data strategist", "data product",
        "data specialist", "head of data", "datenmanager",
    ], isco08="2521", soc2018="15-1243", kldb2010="43"),
    _r("data.quant", "Quantitative Analyst", "data_ai", [
        "quantitative analyst", "quant analyst", "quantitative researcher",
        "quantitative developer", "quant developer", "quant researcher",
        "algorithmic trading developer", "quantitative strategist",
    ], isco08="2120", soc2018="15-2031", kldb2010="72"),
    _r("data.statistician", "Statistician", "data_ai", [
        "statistician", "statistiker", "biostatistician", "statistical programmer",
        "sas programmer", "statistical analyst", "psychometrician",
    ], isco08="2120", soc2018="15-2041", kldb2010="41"),

    # ---------------- Infrastruktur -------------------------------------
    _r("infra.devops", "DevOps Engineer", "infrastructure", [
        "devops engineer", "devops", "devsecops engineer", "ci/cd engineer",
        "automation engineer devops", "devops specialist", "release engineer",
        "kubernetes engineer", "docker engineer", "gitops engineer",
    ], isco08="2522", soc2018="15-1244", kldb2010="43"),
    _r("infra.sre", "Site Reliability Engineer", "infrastructure", [
        "site reliability engineer", "sre", "reliability engineer",
        "production engineer", "systems reliability engineer",
    ], isco08="2522", soc2018="15-1244", kldb2010="43"),
    _r("infra.cloud", "Cloud Engineer", "infrastructure", [
        "cloud engineer", "cloud infrastructure engineer", "aws engineer",
        "azure engineer", "gcp engineer", "cloud architect",
        "cloud solutions architect", "cloud specialist", "cloud operations engineer",
        "cloud native engineer", "cloud administrator",
    ], isco08="2522", soc2018="15-1241", kldb2010="43"),
    _r("infra.systems", "Systems Engineer", "infrastructure", [
        "systems engineer", "system engineer", "systemingenieur",
        "infrastructure engineer", "it infrastructure engineer",
        "systems administrator", "system administrator", "sysadmin",
        "systemadministrator", "linux administrator", "windows administrator",
        "server administrator", "it systemadministrator", "unix administrator",
        "virtualization engineer", "storage engineer", "datacenter engineer",
    ], isco08="2522", soc2018="15-1244", kldb2010="43"),
    _r("infra.network", "Network Engineer", "infrastructure", [
        "network engineer", "netzwerkadministrator", "netzwerktechniker",
        "network administrator", "network architect", "netzwerk engineer",
        "noc engineer", "network operations engineer", "telecom engineer",
        "ingenieur reseau", "voip engineer", "wan engineer",
    ], isco08="2523", soc2018="15-1241", kldb2010="43"),

    # ---------------- Security ------------------------------------------
    _r("security.engineer", "Security Engineer", "security", [
        "security engineer", "information security engineer", "cyber security engineer",
        "cybersecurity engineer", "it security engineer", "sicherheitsingenieur it",
        "application security engineer", "appsec engineer", "cloud security engineer",
        "it security", "it sicherheit", "informationssicherheit", "cyber security",
        "security architect", "sicherheitsarchitekt", "product security engineer",
    ], isco08="2529", soc2018="15-1212", kldb2010="43"),
    _r("security.analyst", "Security Analyst", "security", [
        "security analyst", "information security analyst", "soc analyst",
        "cyber security analyst", "it security analyst", "threat analyst",
        "incident response analyst", "security operations analyst",
        "vulnerability analyst", "penetration tester", "pentester",
        "ethical hacker", "red team operator", "security consultant",
        "it sicherheitsanalyst", "informationssicherheitsbeauftragter",
    ], isco08="2529", soc2018="15-1212", kldb2010="43"),

    # ---------------- Test / QA ------------------------------------------
    _r("quality.qa_engineer", "QA Engineer", "quality", [
        "qa engineer", "quality assurance engineer", "test engineer",
        "software tester", "qa analyst", "test automation engineer",
        "sdet", "software development engineer in test", "qa automation engineer",
        "testingenieur", "testmanager", "qualitaetssicherung software",
        "qa specialist", "manual tester", "testautomatisierer",
        "quality assurance", "qualitaetssicherung", "software testing",
    ], isco08="2519", soc2018="15-1253", kldb2010="43"),
    _r("quality.qm", "Quality Manager", "quality", [
        "quality manager", "qualitaetsmanager", "quality engineer",
        "qualitaetsingenieur", "quality assurance manager", "qm beauftragter",
        "quality control inspector", "qualitaetspruefer", "quality specialist",
        "qualitaetstechniker", "supplier quality engineer", "qhse manager",
    ], isco08="2141", soc2018="17-2112", kldb2010="27"),

    # ---------------- Produkt / Projekt ----------------------------------
    _r("product.manager", "Product Manager", "product", [
        "product manager", "produktmanager", "product owner", "produktverantwortlicher",
        "technical product manager", "senior product manager", "group product manager",
        "digital product manager", "chef de produit", "product lead",
        "data product manager", "ai product manager", "platform product manager",
        "product management", "produktmanagement", "growth product manager",
        "produkt",
    ], isco08="2431", soc2018="13-1082", kldb2010="71"),
    _r("product.analyst", "Product Analyst", "product", [
        "product analyst", "produkt analyst", "product operations analyst",
        "product data analyst", "produktanalyst",
    ], isco08="2431", soc2018="13-1111", kldb2010="71"),
    _r("product.project_manager", "Project Manager", "product", [
        "project manager", "projektmanager", "projektleiter", "project lead",
        "chef de projet", "project coordinator", "projektkoordinator",
        "technical project manager", "it project manager", "pmo",
        "project management officer", "bauleiter projekt", "scrum master",
        "agile coach", "release train engineer", "delivery manager",
        "project engineer", "projektingenieur", "responsabile di progetto",
    ], isco08="2421", soc2018="13-1082", kldb2010="71"),
    _r("product.program_manager", "Program Manager", "product", [
        "program manager", "programmanager", "technical program manager",
        "tpm", "programme manager", "portfolio manager projects",
    ], isco08="2421", soc2018="13-1082", kldb2010="71"),
    _r("product.business_analyst", "Business Analyst", "product", [
        "business analyst", "businessanalyst", "requirements engineer",
        "functional analyst", "it business analyst", "process analyst",
        "prozessanalyst", "systems analyst", "analyste metier",
        "business systems analyst", "fachlicher berater anforderungen",
    ], isco08="2511", soc2018="15-1211", kldb2010="43"),

    # ---------------- Design ----------------------------------------------
    _r("design.product_designer", "Product Designer", "design", [
        "product designer", "ux designer", "ui designer", "ux/ui designer",
        "ui/ux designer", "user experience designer", "interaction designer",
        "digital designer", "produktdesigner", "designer produit", "product design",
        "ux", "user experience",
        "senior product designer", "experience designer", "service designer",
    ], isco08="2166", soc2018="15-1255", kldb2010="93"),
    _r("design.ux_research", "UX Researcher", "design", [
        "ux researcher", "user researcher", "design researcher",
        "usability researcher", "nutzerforscher",
    ], isco08="2166", soc2018="19-3033", kldb2010="93"),
    _r("design.graphic", "Graphic Designer", "design", [
        "graphic designer", "grafikdesigner", "mediengestalter",
        "visual designer", "brand designer", "motion designer",
        "graphiste", "art director", "creative director", "designer grafico",
        "3d artist", "illustrator designer", "packaging designer",
    ], isco08="2166", soc2018="27-1024", kldb2010="93"),

    # ---------------- Forschung -------------------------------------------
    _r("research.scientist", "Research Scientist", "research", [
        "research scientist", "forscher", "wissenschaftlicher mitarbeiter",
        "researcher", "postdoc", "postdoctoral researcher", "academic researcher",
        "chercheur", "principal investigator", "research fellow",
        "scientist", "senior scientist", "laboratory scientist", "lab scientist",
        "chemist", "chemiker", "biologist", "biologe", "physicist", "physiker",
        "clinical research associate", "bioinformatician", "bioinformatiker",
    ], isco08="2131", soc2018="19-1042", kldb2010="41"),
    _r("research.engineer", "Research Engineer", "research", [
        "research engineer", "forschungsingenieur", "r&d engineer",
        "research and development engineer", "entwicklungsingenieur forschung",
        "ingenieur recherche", "applied research engineer",
    ], isco08="2141", soc2018="17-2199", kldb2010="27"),

    # ---------------- IT-Support -------------------------------------------
    _r("it.support", "IT Support Specialist", "it_support", [
        "it support", "technical support engineer", "support engineer",
        "helpdesk", "help desk", "service desk", "it supporter",
        "desktop support", "1st level support", "2nd level support",
        "technical support specialist", "it techniker", "field service technician it",
        "computer field technician", "technischer support", "support specialist",
        "it administrator", "informatiker support", "user support",
    ], isco08="3512", soc2018="15-1232", kldb2010="43"),
    _r("it.sap", "SAP Consultant", "it_support", [
        "sap consultant", "sap berater", "sap developer", "abap developer",
        "sap analyst", "sap specialist", "erp consultant", "erp berater",
        "salesforce developer", "salesforce administrator", "salesforce consultant",
        "dynamics consultant", "servicenow developer", "workday consultant",
        "netsuite consultant", "crm consultant",
    ], isco08="2511", soc2018="15-1211", kldb2010="43"),

    # ---------------- Vertrieb ---------------------------------------------
    _r("sales.account_executive", "Account Executive", "sales", [
        "account executive", "enterprise account executive", "sales executive",
        "strategic account executive", "commercial account executive",
        "mid market account executive", "ae saas", "senior account executive",
    ], isco08="2433", soc2018="41-4012", kldb2010="61"),
    _r("sales.sdr", "Sales Development Representative", "sales", [
        "sales development representative", "sdr", "business development representative",
        "bdr", "lead development representative", "inside sales representative",
        "outbound sales representative", "vertriebsassistenz akquise",
        "appointment setter", "prospecting specialist",
    ], isco08="2433", soc2018="41-3091", kldb2010="61"),
    _r("sales.account_manager", "Account Manager", "sales", [
        "account manager", "key account manager", "kundenbetreuer",
        "client manager", "client partner", "technical account manager",
        "customer account manager", "national account manager",
        "strategic account manager", "gestionnaire de compte", "betreuer key accounts",
    ], isco08="2433", soc2018="41-4012", kldb2010="61"),
    _r("sales.manager", "Sales Manager", "sales", [
        "sales manager", "vertriebsleiter", "vertriebsmanager", "head of sales",
        "regional sales manager", "area sales manager", "district sales manager",
        "verkaufsleiter", "responsable commercial", "sales director",
        "leiter vertrieb", "leitung vertrieb", "vertriebsleitung",
        "territory manager", "gebietsverkaufsleiter", "sales lead",
    ], isco08="1221", soc2018="11-2022", kldb2010="61"),
    _r("sales.representative", "Sales Representative", "sales", [
        "sales representative", "vertriebsmitarbeiter", "aussendienstmitarbeiter",
        "sales rep", "field sales representative", "commercial",
        "employe commercial", "conseiller de vente", "sales advisor", "visual merchandiser",
        "student marketeer", "sales - optical",
        "vertriebsbeauftragter", "handelsvertreter", "medical sales representative",
        "vertrieb", "aussendienst",
        "pharmareferent", "sales agent", "sales consultant", "kundenberater vertrieb",
        "immobilienmakler", "real estate agent",
    ], isco08="3322", soc2018="41-4012", kldb2010="61"),
    _r("sales.engineer", "Sales Engineer", "sales", [
        "sales engineer", "solutions engineer", "solution engineer",
        "presales engineer", "pre-sales consultant", "technical sales engineer",
        "vertriebsingenieur", "field application engineer",
        "customer engineer", "solutions consultant", "presales consultant",
    ], isco08="2433", soc2018="41-9031", kldb2010="61"),
    _r("sales.business_development", "Business Development Manager", "sales", [
        "business development manager", "business development",
        "business development director", "geschaeftsentwicklung",
        "partnerships manager", "partner manager", "alliance manager",
        "channel manager", "expansion manager", "growth manager",
    ], isco08="2421", soc2018="11-2022", kldb2010="61"),

    # ---------------- Marketing ---------------------------------------------
    _r("marketing.manager", "Marketing Manager", "marketing", [
        "marketing manager", "marketingmanager", "marketing lead",
        "head of marketing", "brand manager", "markenmanager",
        "product marketing manager", "digital marketing manager",
        "responsable marketing", "marketing specialist", "marketing coordinator",
        "campaign manager", "kampagnenmanager", "marketing",
        "growth marketing manager", "demand generation manager",
        "field marketing manager", "trade marketing manager",
    ], isco08="1221", soc2018="11-2021", kldb2010="92"),
    _r("marketing.performance", "Performance Marketing Manager", "marketing", [
        "performance marketing manager", "paid media manager", "sea manager",
        "ppc specialist", "google ads manager", "paid social manager",
        "online marketing manager", "growth hacker", "crm marketing manager",
        "email marketing manager", "lifecycle marketing manager",
    ], isco08="2431", soc2018="13-1161", kldb2010="92"),
    _r("marketing.seo_content", "SEO / Content Manager", "marketing", [
        "seo manager", "seo specialist", "content manager", "content marketing manager",
        "content creator", "redakteur", "copywriter", "texter", "editor",
        "social media manager", "community manager", "content strategist",
        "technical writer", "technischer redakteur", "documentation writer",
        "journalist", "content producer",
    ], isco08="2642", soc2018="27-3042", kldb2010="92"),
    _r("marketing.pr", "PR / Communications Manager", "marketing", [
        "pr manager", "public relations manager", "communications manager",
        "kommunikationsmanager", "pressesprecher", "corporate communications",
        "internal communications manager", "unternehmenskommunikation",
    ], isco08="2432", soc2018="11-2032", kldb2010="92"),

    # ---------------- Customer ----------------------------------------------
    _r("customer.success", "Customer Success Manager", "customer", [
        "customer success manager", "csm", "client success manager",
        "customer success", "kundenerfolgsmanager", "customer experience manager",
        "member experience manager", "customer onboarding manager",
        "renewals manager", "customer engagement manager",
    ], isco08="2433", soc2018="41-3091", kldb2010="61"),
    _r("customer.service", "Customer Service Representative", "customer", [
        "customer service representative", "customer service rep",
        "kundenservice mitarbeiter", "kundenbetreuung", "customer support",
        "customer service agent", "call center agent", "servicemitarbeiter",
        "customer care", "customer service", "client services",
        "conseiller clientele", "customer advisor", "guest services",
        "retail customer service", "customer service advisor",
        "sachbearbeiter kundenservice", "hote de caisse", "reception",
        "receptionist", "empfangsmitarbeiter",
    ], isco08="4222", soc2018="43-4051", kldb2010="62"),

    # ---------------- HR ------------------------------------------------------
    _r("hr.recruiter", "Recruiter", "hr", [
        "recruiter", "technical recruiter", "talent acquisition",
        "talent acquisition specialist", "personalreferent recruiting",
        "recruiting specialist", "sourcing specialist", "talent partner",
        "personalberater", "headhunter", "chargé de recrutement",
        "recruitment consultant", "talent acquisition partner", "recruiting",
        "personalbeschaffung",
    ], isco08="2423", soc2018="13-1071", kldb2010="71"),
    _r("hr.generalist", "HR Manager", "hr", [
        "hr manager", "personalleiter", "human resources manager",
        "hr business partner", "hrbp", "hr generalist", "personalreferent",
        "people operations", "peopleops", "people partner", "hr specialist",
        "personalsachbearbeiter", "responsable rh", "hr administrator",
        "personalentwickler", "learning and development manager", "hr business",
        "leiter personal", "leitung personal", "personalleitung",
        "benefits services representative", "client benefits representative",
        "enrollment specialist",
        "compensation and benefits manager", "payroll specialist",
        "lohnbuchhalter", "entgeltabrechnung", "hr director", "people manager hr",
    ], isco08="1212", soc2018="11-3121", kldb2010="71"),

    # ---------------- Finanzen ------------------------------------------------
    _r("finance.accountant", "Accountant", "finance", [
        "accountant", "buchhalter", "finanzbuchhalter", "bilanzbuchhalter",
        "staff accountant", "senior accountant", "accounts payable",
        "accounts receivable", "kreditorenbuchhalter", "debitorenbuchhalter",
        "comptable", "general ledger accountant", "steuerfachangestellter",
        "tax accountant", "steuerberater", "auditor", "wirtschaftspruefer",
        "internal auditor", "revisor", "accounting specialist", "accounting manager", "buchhaltung",
        "rechnungswesen", "accounting",
    ], isco08="2411", soc2018="13-2011", kldb2010="72"),
    _r("finance.controller", "Controller", "finance", [
        "controller", "controlling", "financial controller", "business controller",
        "kostenrechner", "cost controller", "controller finance",
        "kaufmaennischer leiter controlling",
    ], isco08="2411", soc2018="13-2011", kldb2010="72"),
    _r("finance.analyst", "Financial Analyst", "finance", [
        "financial analyst", "finanzanalyst", "fp&a analyst", "fp&a",
        "finance analyst", "investment analyst", "credit analyst",
        "treasury analyst", "corporate finance analyst", "m&a analyst",
        "equity research analyst", "risk analyst", "actuary", "aktuar",
        "versicherungsmathematiker", "finanzberater", "financial advisor",
        "anlageberater", "portfolio manager", "asset manager",
    ], isco08="2413", soc2018="13-2051", kldb2010="72"),
    _r("finance.manager", "Finance Manager", "finance", [
        "finance manager", "finanzmanager", "head of finance", "leiter finanzen",
        "kaufmaennischer leiter", "treasurer", "director of finance",
        "finanzleiter", "responsable financier", "leiter finanzen",
        "leitung finanzen", "leiter rechnungswesen",
    ], isco08="1211", soc2018="11-3031", kldb2010="72"),

    # ---------------- Recht ---------------------------------------------------
    _r("legal.counsel", "Legal Counsel", "legal", [
        "legal counsel", "syndikusanwalt", "rechtsanwalt", "jurist",
        "in-house counsel", "general counsel", "attorney", "lawyer",
        "juriste", "avvocato", "legal advisor", "legal manager",
        "contract manager legal", "vertragsmanager recht",
    ], isco08="2611", soc2018="23-1011", kldb2010="73"),
    _r("legal.compliance", "Compliance Officer", "legal", [
        "compliance officer", "compliance manager", "aml analyst",
        "anti money laundering", "kyc analyst", "geldwaeschebeauftragter",
        "data protection officer", "datenschutzbeauftragter", "privacy counsel",
        "regulatory affairs manager", "risk and compliance manager",
    ], isco08="2619", soc2018="13-1041", kldb2010="73"),
    _r("legal.paralegal", "Paralegal", "legal", [
        "paralegal", "rechtsanwaltsfachangestellte", "legal assistant",
        "notarfachangestellte", "legal operations specialist",
    ], isco08="3411", soc2018="23-2011", kldb2010="73"),

    # ---------------- Operations ----------------------------------------------
    _r("operations.manager", "Operations Manager", "operations", [
        "operations manager", "betriebsleiter", "operations lead",
        "head of operations", "business operations manager", "bizops",
        "operations specialist", "operations coordinator", "operations",
        "responsable des operations", "general operations manager",
        "site manager operations", "workforce manager",
    ], isco08="1219", soc2018="11-1021", kldb2010="71"),
    _r("operations.strategy", "Strategy Manager", "operations", [
        "strategy manager", "corporate strategy", "strategy analyst",
        "chief of staff", "business strategist", "strategic planning manager",
        "unternehmensentwicklung", "corporate development manager",
        "transformation manager", "change manager",
    ], isco08="2421", soc2018="13-1111", kldb2010="71"),
    _r("operations.facility", "Facility Manager", "operations", [
        "facility manager", "facilities manager", "hausmeister",
        "gebaeudemanagement", "objektleiter", "caretaker",
        "janitorial maintenance", "janitor", "reinigungskraft", "cleaner",
        "building maintenance", "housekeeping", "raumpfleger",
    ], isco08="5153", soc2018="37-2011", kldb2010="54"),

    # ---------------- Supply Chain ---------------------------------------------
    _r("supply.manager", "Supply Chain Manager", "supply_chain", [
        "supply chain manager", "supply chain specialist", "logistics manager",
        "logistikleiter", "materialplaner", "demand planner", "supply planner",
        "production planner", "produktionsplaner", "disponent",
        "supply chain analyst", "logistikkoordinator", "transportleiter", "leiter logistik",
        "leitung logistik", "leiter lager",
        "supply chain", "logistik", "logistics",
        "responsable logistique", "planner", "s&op manager",
    ], isco08="1324", soc2018="13-1081", kldb2010="51"),
    _r("supply.procurement", "Procurement Manager", "supply_chain", [
        "procurement manager", "einkaeufer", "strategischer einkaeufer",
        "purchasing manager", "buyer", "category manager procurement",
        "sourcing manager", "acheteur", "einkaufsleiter", "vendor manager", "leiter einkauf", "leitung einkauf",
        "supplier manager", "contract manager procurement", "einkauf",
        "procurement", "beschaffung",
    ], isco08="1324", soc2018="13-1023", kldb2010="61"),
    _r("supply.warehouse", "Warehouse Associate", "supply_chain", [
        "warehouse", "lagerist", "lagermitarbeiter", "warehouse associate",
        "warehouse operative", "kommissionierer", "picker packer",
        "fachkraft fuer lagerlogistik", "magazziniere", "operateur logistique",
        "material handler", "stock associate", "inventory associate",
        "fiel de armazem", "warehouse worker", "preparateur de commandes",
    ], isco08="9333", soc2018="53-7062", kldb2010="513"),

    # ---------------- Beratung --------------------------------------------------
    _r("consulting.consultant", "Consultant", "consulting", [
        "consultant", "berater", "management consultant", "unternehmensberater",
        "strategy consultant", "senior consultant", "associate consultant",
        "it consultant", "it berater", "technology consultant",
        "implementation consultant", "solution consultant", "consulente",
        "deployment strategist", "forward deployed", "engagement manager",
        "conseiller", "advisory consultant", "transformation consultant",
    ], isco08="2421", soc2018="13-1111", kldb2010="71"),

    # ---------------- Management -------------------------------------------------
    _r("management.executive", "Executive (C-Level)", "management", [
        "chief executive officer", "ceo", "chief technology officer", "cto",
        "chief financial officer", "cfo", "chief operating officer", "coo",
        "chief information officer", "cio", "chief marketing officer", "cmo",
        "chief product officer", "cpo", "chief data officer", "cdo",
        "chief information security officer", "ciso", "chief revenue officer",
        "cro", "chief people officer", "geschaeftsfuehrer", "vorstand",
        "managing director", "president", "vice president", "vp engineering",
        "vp of engineering", "svp", "founder", "co-founder", "gruender",
        "vp sales", "vp marketing", "vp product", "managing partner",
    ], isco08="1120", soc2018="11-1011", kldb2010="71"),
    _r("management.engineering", "Engineering Manager", "management", [
        "engineering manager", "entwicklungsleiter", "head of engineering",
        "software engineering manager", "director of engineering",
        "technical manager", "development manager", "it manager",
        "head of it", "it leiter", "head of technology", "director of technology",
        "leiter softwareentwicklung", "team lead engineering",
        "leiter entwicklung", "leitung entwicklung", "leiter it", "leitung it",
    ], isco08="1330", soc2018="11-3021", kldb2010="43"),
    _r("management.general", "General Manager", "management", [
        "general manager", "store manager", "filialleiter", "branch manager",
        "restaurant manager", "assistant manager", "shift manager",
        "district manager", "regional manager", "area manager", "department manager",
        "abteilungsleiter", "management training program", "team leader",
        "teamleiter", "shift supervisor", "schichtleiter",
        "niederlassungsleiter", "standortleiter", "gerente", "direttore",
        "site leader", "market manager", "hotel manager", "hoteldirektor",
    ], isco08="1420", soc2018="11-1021", kldb2010="71"),

    # ---------------- Technik / Ingenieurwesen -------------------------------------
    _r("eng.mechanical", "Mechanical Engineer", "engineering_industrial", [
        "mechanical engineer", "maschinenbauingenieur", "konstrukteur",
        "design engineer mechanical", "cad konstrukteur", "ingenieur mecanique",
        "design engineer", "product engineer", "produktentwickler",
        "product engineer mechanical", "mechanical design engineer",
        "berechnungsingenieur", "simulationsingenieur", "cae engineer",
    ], isco08="2144", soc2018="17-2141", kldb2010="27"),
    _r("eng.electrical", "Electrical Engineer", "engineering_industrial", [
        "electrical engineer", "elektroingenieur", "elektrotechniker",
        "hardware engineer", "hardwareentwickler", "electronics engineer",
        "pcb designer", "power engineer", "energietechniker",
        "ingenieur electrique", "elektrokonstrukteur", "fpga engineer",
        "asic engineer", "rf engineer", "hochfrequenztechniker",
    ], isco08="2151", soc2018="17-2071", kldb2010="26"),
    _r("eng.civil", "Civil Engineer", "engineering_industrial", [
        "civil engineer", "bauingenieur", "structural engineer", "statiker",
        "tragwerksplaner", "quantity surveyor", "cost manager construction", "cost manager",
        "site engineer", "bauleiter", "construction manager", "tiefbauingenieur",
        "ingenieur civil", "geotechnical engineer", "surveyor",
        "architekt", "architect building", "urban planner", "stadtplaner",
    ], isco08="2142", soc2018="17-2051", kldb2010="31"),
    _r("eng.industrial", "Industrial / Manufacturing Engineer", "engineering_industrial", [
        "industrial engineer", "manufacturing engineer", "wirtschaftsingenieur",
        "fertigungsingenieur", "prozessingenieur", "process engineer",
        "production engineer manufacturing", "produktionsingenieur",
        "lean manager", "methods engineer", "verfahrensingenieur",
        "automation engineer", "automatisierungstechniker", "sps programmierer",
        "plc engineer", "robotics engineer", "robotik ingenieur",
    ], isco08="2141", soc2018="17-2112", kldb2010="27"),
    _r("eng.chemical", "Chemical / Process Engineer", "engineering_industrial", [
        "chemical engineer", "chemieingenieur", "verfahrenstechniker",
        "pharmaceutical engineer", "biotech engineer", "food technologist",
        "lebensmitteltechnologe", "materials engineer", "werkstoffingenieur",
    ], isco08="2145", soc2018="17-2041", kldb2010="41"),
    _r("eng.hse", "HSE / Environmental Specialist", "engineering_industrial", [
        "hse manager", "ehs manager", "health and safety manager",
        "arbeitssicherheit", "sicherheitsfachkraft", "umweltingenieur",
        "environmental engineer", "sustainability manager",
        "nachhaltigkeitsmanager", "esg manager", "hse advisor",
    ], isco08="2263", soc2018="19-5011", kldb2010="42"),

    # ---------------- Handwerk / Produktion -------------------------------------
    _r("trades.maintenance", "Maintenance Technician", "trades", [
        "maintenance technician", "instandhaltungstechniker",
        "wartungstechniker", "servicetechniker", "field service technician",
        "instandhaltung", "wartung",
        "technicien de maintenance", "mechatroniker", "industriemechaniker",
        "maintenance engineer", "betriebstechniker", "anlagenmechaniker",
        "elektroniker fuer betriebstechnik", "haustechniker",
    ], isco08="7233", soc2018="49-9071", kldb2010="26"),
    _r("trades.automotive", "Automotive Technician", "trades", [
        "automotive technician", "kfz mechatroniker", "kfz mechaniker",
        "automotive service technician", "vehicle technician", "mechaniker",
        "automotive service advisor", "automotive service manager",
        "general service technician", "tire technician", "auto mechanic",
        "controleur technique automobile", "nutzfahrzeugmechaniker",
    ], isco08="7231", soc2018="49-3023", kldb2010="25"),
    _r("trades.electrician", "Electrician", "trades", [
        "electrician", "elektriker", "elektroniker", "elektroinstallateur",
        "electricien", "elettricista", "energieanlagenelektroniker",
    ], isco08="7411", soc2018="47-2111", kldb2010="26"),
    _r("trades.construction", "Construction Worker", "trades", [
        "construction worker", "bauarbeiter", "maurer", "zimmerer",
        "trockenbauer", "dachdecker", "fliesenleger", "maler und lackierer",
        "installateur", "sanitaer heizung klima", "shk", "hvac technician",
        "plumber", "klempner", "schweisser", "welder", "carpenter",
        "landscaper", "gaertner", "gardener", "roofer", "painter decorator",
    ], isco08="7112", soc2018="47-2061", kldb2010="32"),
    _r("trades.production", "Production Worker", "trades", [
        "production worker", "produktionsmitarbeiter", "produktionshelfer",
        "maschinenbediener", "machine operator", "cnc fraeser", "cnc dreher",
        "cnc operator", "zerspanungsmechaniker", "montagemitarbeiter",
        "assembler", "fertigungsmitarbeiter", "operaio", "operateur de production",
        "line operator", "production associate", "helfer produktion",
        "production", "team member production", "fertigungssteuerer",
    ], isco08="8189", soc2018="51-9199", kldb2010="24"),

    # ---------------- Gesundheit ----------------------------------------------
    _r("health.nurse", "Nurse", "healthcare", [
        "nurse", "registered nurse", "krankenschwester", "krankenpfleger",
        "pflegefachkraft", "gesundheits und krankenpfleger", "staff nurse",
        "infirmier", "infirmiere", "altenpfleger", "pflegehelfer",
        "healthcare assistant", "care assistant", "care professional",
        "pflegekraft", "aide soignant", "nursing assistant", "support worker",
        "pflege", "krankenpflege", "altenpflege",
        "home care assistant", "betreuungskraft", "medizinische fachangestellte",
        "mfa", "arzthelferin", "pflegedienstleitung",
    ], isco08="2221", soc2018="29-1141", kldb2010="81"),
    _r("health.physician", "Physician", "healthcare", [
        "physician", "arzt", "aerztin", "doctor", "medecin", "facharzt",
        "oberarzt", "assistenzarzt", "chefarzt", "surgeon", "chirurg",
        "anesthesiologist", "radiologist", "psychiatrist", "veterinarian",
        "tierarzt", "dentist", "zahnarzt", "dvm", "general practitioner",
    ], isco08="2211", soc2018="29-1215", kldb2010="814"),
    _r("health.therapist", "Therapist", "healthcare", [
        "therapist", "physiotherapist", "physiotherapeut", "ergotherapeut",
        "occupational therapist", "speech language pathologist",
        "logopaede", "psychotherapist", "psychologe", "psychologist",
        "behavior technician", "registered behavior technician", "rbt",
        "board certified behavior analyst", "bcba", "behaviour analyst",
        "counselor", "sozialpaedagoge", "social worker", "sozialarbeiter",
        "kinesitherapeute", "speech language pathology assistant",
    ], isco08="2269", soc2018="29-1129", kldb2010="817"),
    _r("health.pharmacy", "Pharmacist / Pharmacy Technician", "healthcare", [
        "pharmacist", "apotheker", "pta", "pharmazeutisch technische assistentin",
        "pharmacy technician", "pharmareferent apotheke", "optometrist",
        "optiker", "augenoptiker", "hoerakustiker", "medical technologist",
        "mta", "laborant", "lab technician", "medizinische technologin",
    ], isco08="2262", soc2018="29-1051", kldb2010="82"),

    # ---------------- Bildung -------------------------------------------------
    _r("education.teacher", "Teacher", "education", [
        "teacher", "lehrer", "dozent", "lecturer", "professor", "instructor",
        "trainer", "ausbilder", "erzieher", "kindergaertner", "educator",
        "nachhilfelehrer", "enseignant", "insegnante", "tutor",
        "teaching assistant", "paedagogische fachkraft", "schulbegleiter",
        "fachlehrer", "kursleiter", "coach education",
    ], isco08="2330", soc2018="25-2031", kldb2010="84"),

    # ---------------- Gastronomie ---------------------------------------------
    _r("hospitality.chef", "Chef / Cook", "hospitality", [
        "chef", "koch", "koechin", "cook", "sous chef", "chef de partie",
        "commis de cuisine", "line cook", "head chef", "kuechenchef",
        "demi chef de partie", "prep cook", "pastry chef", "patissier",
        "baker", "baecker", "konditor", "butcher", "boucher", "metzger",
        "kitchen assistant", "kuechenhilfe", "catering assistant",
        "speisenzubereitung", "grillardin", "deli baker", "sandwich artist",
        "cuisinier", "kitchen", "kueche", "deli production team member",
        "kitchen porter", "spuelkraft",
    ], isco08="5120", soc2018="35-2014", kldb2010="293"),
    _r("hospitality.service", "Waiter / Service Staff", "hospitality", [
        "waiter", "waitress", "kellner", "servicekraft", "bar staff",
        "bartender", "barista", "serveur", "cameriere", "bar & waiting staff",
        "restaurantfachmann", "hotelfachmann", "front office agent",
        "rezeptionist hotel", "housekeeping attendant", "zimmermaedchen",
        "food service worker", "team member restaurant", "crew member",
        "runner restaurant", "host hostess",
    ], isco08="5131", soc2018="35-3031", kldb2010="633"),

    # ---------------- Handel --------------------------------------------------
    _r("retail.sales_assistant", "Retail Sales Assistant", "retail", [
        "verkaeufer", "verkaeuferin", "sales assistant", "sales associate",
        "retail assistant", "shop assistant", "vendeur", "vendeuse",
        "addetto alle vendite", "sprzedawca", "verkoopmedewerker",
        "einzelhandelskaufmann", "kaufmann im einzelhandel", "store associate",
        "key holder", "retail associate", "verkauf", "verkaufsberater",
        "fachverkaeufer", "sales floor associate", "customer assistant",
    ], isco08="5223", soc2018="41-2031", kldb2010="62"),
    _r("retail.cashier", "Cashier", "retail", [
        "cashier", "kassierer", "kassenmitarbeiter", "caissier",
        "checkout assistant", "kassenkraft", "front end cashier",
    ], isco08="5230", soc2018="41-2011", kldb2010="62"),

    # ---------------- Transport ------------------------------------------------
    _r("transport.driver", "Driver", "transport", [
        "driver", "fahrer", "delivery driver", "lkw fahrer", "truck driver",
        "berufskraftfahrer", "chauffeur", "auslieferungsfahrer", "kurierfahrer",
        "conducteur", "autista", "bus driver", "busfahrer", "cdl driver",
        "van driver", "mapping data collection driver", "zusteller",
        "paketzusteller", "forklift driver", "staplerfahrer",
    ], isco08="8332", soc2018="53-3032", kldb2010="521"),

    # ---------------- Administration -------------------------------------------
    _r("admin.assistant", "Administrative Assistant", "admin", [
        "administrative assistant", "executive assistant", "assistenz der geschaeftsfuehrung",
        "office manager", "buerokaufmann", "sekretaerin", "secretary",
        "teamassistenz", "sachbearbeiter", "verwaltungsangestellter",
        "assistant administratif", "office administrator", "data entry clerk",
        "agent de saisie", "clerk", "backoffice mitarbeiter", "empfang",
        "personal assistant", "company secretary", "assistenz",
    ], isco08="4120", soc2018="43-6014", kldb2010="714"),

    _r("other.hairdresser", "Hairdresser / Beauty", "other", [
        "hairdresser", "friseur", "coiffeur", "coiffeuse", "hair stylist",
        "barber", "kosmetikerin", "beautician", "nail technician",
        "masseur", "podologe", "fusspfleger",
    ], isco08="5141", soc2018="39-5012", kldb2010="823"),

    # ---------------- bewusst unspezifische Sammeltitel --------------------------
    _r("generic.engineer", "Engineer (unspezifisch)", "generic", [
        "engineer", "ingenieur", "engineering", "technicien", "ingegnere",
    ], isco08="2149", soc2018="17-2199", kldb2010="27"),
    _r("generic.manager", "Manager (unspezifisch)", "generic", [
        "manager", "managerin", "leiter", "leitung", "responsable",
    ], isco08="1219", soc2018="11-1021", kldb2010="71"),
    _r("generic.analyst", "Analyst (unspezifisch)", "generic", [
        "analyst", "analystin", "analyste", "analista", "research analyst",
    ], isco08="2422", soc2018="13-1111", kldb2010="71"),
    _r("generic.specialist", "Specialist (unspezifisch)", "generic", [
        "specialist", "spezialist", "fachkraft", "referent", "expert",
        "coordinator", "koordinator", "coordinateur",
    ], isco08="2422", soc2018="13-1199", kldb2010="71"),
    _r("generic.architect", "Architect (unspezifisch)", "generic", [
        "architect",
    ], isco08="2511", soc2018="15-1299", kldb2010="43"),
    _r("generic.associate", "Associate (unspezifisch)", "generic", [
        "associate", "mitarbeiter", "team member", "crew", "staff member",
        "employee", "collaborateur", "agent",
    ], isco08="4419", soc2018="43-9199", kldb2010="71"),
    _r("generic.technician", "Technician (unspezifisch)", "generic", [
        "technician", "techniker", "tecnico", "technical",
    ], isco08="3119", soc2018="17-3029", kldb2010="26"),
    _r("generic.director", "Director (unspezifisch)", "generic", [
        "director", "direktor", "directeur", "head",
    ], isco08="1120", soc2018="11-1021", kldb2010="71"),

    # ---------------- Sicherheit / Schutz ---------------------------------------
    _r("other.security_guard", "Security Guard", "other", [
        "security guard", "sicherheitsmitarbeiter", "wachmann",
        "objektschutz", "werkschutz", "agent de securite", "doorman",
        "loss prevention officer", "traffic control flagger",
    ], isco08="5414", soc2018="33-9032", kldb2010="531"),
]

ROLES_BY_CODE: dict[str, Role] = {r.code: r for r in ROLES}

#: Sammelknoten fuer alles, was keine Regel und kein Modell zuordnen kann.
UNKNOWN = Role(code="other.unknown", label="Nicht zugeordnet", family="other")
ROLES_BY_CODE[UNKNOWN.code] = UNKNOWN


def role(code: str) -> Role:
    return ROLES_BY_CODE.get(code, UNKNOWN)


def all_aliases() -> list[tuple[str, str]]:
    """(Alias, Code) fuer jede Rolle - Trainingsmaterial und Gazetteer."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for r in ROLES:
        for alias in (r.label.lower(), *r.aliases):
            if alias in seen:
                continue
            seen.add(alias)
            out.append((alias, r.code))
    return out


def alias_conflicts() -> dict[str, list[str]]:
    """Aliase, die auf mehrere Rollen zeigen - sollte leer sein."""
    owners: dict[str, list[str]] = {}
    for r in ROLES:
        for alias in (r.label.lower(), *r.aliases):
            owners.setdefault(alias, []).append(r.code)
    return {a: c for a, c in owners.items() if len(set(c)) > 1}


def summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in ROLES:
        counts[r.family] = counts.get(r.family, 0) + 1
    return counts
