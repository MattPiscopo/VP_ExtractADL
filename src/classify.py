"""Classification and Business Development (BD) tagging engine for ADL publications."""
import re
from typing import Dict, List, Tuple

DIRECT_ENUR_PATTERNS = [
    r"energy[,\s]+utilities[,\s]+(&|and)[,\s]+resources",
    r"^energy[,\s]+utilities",
    r"energy\b",
    r"utilities\b",
]

SUBSECTOR_RULES = [
    (
        "Power generation",
        re.compile(r"\b(nuclear|offshore wind|onshore wind|solar|photovoltaic|power plant|power generation|thermal power|hydroelectric|turbines?)\b", re.I),
        "Generation strategy & asset optimization"
    ),
    (
        "Electricity transmission and distribution",
        re.compile(r"\b(transmission|distribution grid|grid modernization|smart grid|substations?|tso\b|dso\b|grid congestion|grid flexibility|interconnector|system operator)\b", re.I),
        "Grid modernization & network reliability"
    ),
    (
        "Energy retail and customer solutions",
        re.compile(r"\b(energy retail|tariffs?|smart meter|residential flexibility|demand[- ]side|heat pumps?|b2b energy|customer propositions?|behind[- ]the[- ]meter)\b", re.I),
        "Customer propositions & retail flexibility"
    ),
    (
        "Oil and gas",
        re.compile(r"\b(oil\b|gas\b|lng\b|liquefied natural gas|pipeline|upstream|midstream|downstream|refin(ing|ery)|petroleum|exploration & production)\b", re.I),
        "Oil & gas transition & operational efficiency"
    ),
    (
        "Hydrogen and alternative fuels",
        re.compile(r"\b(hydrogen|green hydrogen|blue hydrogen|clean hydrogen|ammonia|e[- ]fuels?|synthetic fuels?|biomethane|biofuels?|ccus|carbon capture)\b", re.I),
        "Hydrogen infrastructure & clean fuel strategy"
    ),
    (
        "Chemicals and petrochemicals",
        re.compile(r"\b(chemical|petrochemical|polymers?|plastics? recycling|feedstocks?|circular chemistry|specialty chemicals)\b", re.I),
        "Chemical sector decarbonization & circularity"
    ),
    (
        "Mining and resources",
        re.compile(r"\b(mining|critical minerals|battery metals|lithium|copper|nickel|cobalt|rare earths?|ores?|metallurgy|sustainable mining)\b", re.I),
        "Critical minerals & sustainable mining operations"
    ),
    (
        "Water and wastewater",
        re.compile(r"\b(water\b|wastewater|desalination|circular water|water utility|water management|effluents?)\b", re.I),
        "Water security & circular utility management"
    ),
    (
        "Energy transition and decarbonization",
        re.compile(r"\b(energy transition|decarboni[sz]ation|net[- ]zero|carbon footprint|ghg|greenhouse gas|renewable energy|rec\b|recs\b|clean energy|sustainability)\b", re.I),
        "Decarbonization strategy & clean energy transition"
    ),
    (
        "Energy infrastructure and investment",
        re.compile(r"\b(capital project|infrastructure investment|energy finance|rab\b|regulatory asset base|asset management|m&a|mergers? and acquisitions?)\b", re.I),
        "Energy infrastructure financing & M&A"
    ),
    (
        "Regulation and market design",
        re.compile(r"\b(regulation|regulatory|market design|capacity market|network codes?|green deal|fit for 55|emissions? trading|ets\b|tariff design)\b", re.I),
        "Regulatory compliance & market design"
    ),
    (
        "AI, digital and operational transformation",
        re.compile(r"\b(ai\b|artificial intelligence|machine learning|digital transformation|predictive maintenance|digital twin|iot\b|automation|operating model)\b", re.I),
        "AI & digital transformation for capital assets"
    ),
]

CORE_ENERGY_TERMS = re.compile(
    r"\b(energy|electric|electricity|hydrogen|decarboni[sz]|climat|water|grid|nuclear|mining|chemical|utility|utilities|renewable|carbon|battery|batteries|ev\b|mobility readiness|cleantech|sustainable|sustainability)\b",
    re.I,
)

EXCLUDED_NON_ENUR_TOPICS = re.compile(
    r"\b(music royalty|royalty administration|bank tokenization|education value chain|classroom to career|telecom roaming|broadband billing|hospital management|pharma commercialization)\b",
    re.I,
)


def classify_publication(
    industries_list: List[str],
    title: str,
    subtitle: str,
    body: str,
    services_list: List[str],
    challenges_list: List[str],
) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
    """
    Classify publication into:
    - ENUR Relevance: 'Direct ENUR' | 'Cross-practice' | 'Other / Non-ENUR'
    - ENUR Subsector: Primary subsector or 'Non-ENUR'
    - BD Topics: list of relevant consulting topics
    - Topic Mapping: list of dicts with theme, potential relevance rationale
    """
    all_industries_str = " ".join(industries_list).lower()
    full_text = " ".join([
        title,
        subtitle,
        body,
        " ".join(services_list),
        " ".join(challenges_list),
    ]).lower()

    # 1. Determine Direct ENUR
    is_direct = any(re.search(pat, all_industries_str, re.I) for pat in DIRECT_ENUR_PATTERNS)

    matched_subsectors = []
    topic_mappings = []

    for subsector_name, regex, bd_theme in SUBSECTOR_RULES:
        if regex.search(full_text):
            matched_subsectors.append(subsector_name)
            topic_mappings.append({
                "subsector": subsector_name,
                "theme": bd_theme,
                "potential_relevance": f"Consulting opportunity in {subsector_name.lower()}: {bd_theme}",
            })

    # If direct ENUR but no specific subsector regex matched, default to general transition
    if is_direct and not matched_subsectors:
        matched_subsectors.append("Energy transition and decarbonization")
        topic_mappings.append({
            "subsector": "Energy transition and decarbonization",
            "theme": "Decarbonization strategy & clean energy transition",
            "potential_relevance": "Strategic transformation in energy, utilities & resources",
        })

    # 2. Check for explicit non-ENUR topics (e.g. music royalties, education value chain, etc.)
    is_excluded_niche = bool(EXCLUDED_NON_ENUR_TOPICS.search(full_text))

    # 3. Determine Cross-practice vs Other
    if is_direct:
        relevance = "Direct ENUR"
        primary_subsector = matched_subsectors[0]
    elif is_excluded_niche:
        relevance = "Other / Non-ENUR"
        primary_subsector = "Non-ENUR"
        topic_mappings = []
    elif CORE_ENERGY_TERMS.search(full_text):
        relevance = "Cross-practice"
        primary_subsector = matched_subsectors[0] if matched_subsectors else "Energy transition and decarbonization"
        if not topic_mappings:
            topic_mappings.append({
                "subsector": primary_subsector,
                "theme": "Cross-sector decarbonization & transition",
                "potential_relevance": "Cross-practice relevance to industrial & energy clients",
            })
    elif matched_subsectors and ("ai" in full_text or "digital transformation" in full_text):
        # Broad enterprise/strategy AI publications (e.g. The AI first organization)
        relevance = "Cross-practice"
        primary_subsector = "AI, digital and operational transformation"
    else:
        relevance = "Other / Non-ENUR"
        primary_subsector = "Non-ENUR"
        topic_mappings = []

    bd_topics = [t["theme"] for t in topic_mappings]
    return relevance, primary_subsector, bd_topics, topic_mappings
