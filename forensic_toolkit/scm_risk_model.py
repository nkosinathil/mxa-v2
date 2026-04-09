# scm_risk_model.py
# Enhanced deterministic SCM/procurement risk model based on Mantzaris research
# WITH FALSE POSITIVE REDUCTION IMPROVEMENTS

from __future__ import annotations

from typing import List, Dict, Tuple
import re
from datetime import datetime
from collections import Counter

# Procurement stages as defined in the Mantzaris paper (p.4)
SCM_STAGES = [
    "Pre-tender/Planning",           # Needs assessment, planning, budgeting
    "Specs/Requirements",             # Definition of requirements, specifications
    "Procedure Choice",                # Choice of procurement procedure
    "Tendering",                        # Invitation, pre-qualification, bidding
    "Evaluation & Award",               # Bid evaluation, assessment, award
    "Post-award/Contract Mgmt",         # Contract management, monitoring
    "Order & Payment",                   # Ordering, receiving, payment
    "Not procurement-related",
]

# Enhanced indicator keywords based on Mantzaris p.5-9
INDICATOR_KEYWORDS: Dict[str, List[str]] = {
    # Principal/agent issues (Mantzaris p.5)
    "Principal/agent conflict": [
        "principal", "agent", "representative", "authorized", "delegated",
        "acting on behalf", "proxy", "mandate"
    ],
    
    # Urgency / emergency procurement pressure (Mantzaris p.5)
    "Urgency / emergency procurement pressure": [
        "urgent", "asap", "emergency", "immediate", "fast track", "bypass", 
        "deviation", "expedite", "rush", "critical need", "last minute",
        "time sensitive", "deadline pressure"
    ],
    
    # Reduced competition / single supplier / limited quotes (Mantzaris p.3)
    "Reduced competition / single supplier": [
        "single supplier", "sole source", "only supplier", "limited quotations", 
        "limited quotes", "one quote", "only quote", "3 quotes waived", 
        "three quotes waived", "closed tender", "restricted tender",
        "deviation from competitive bidding", "non-competitive", "direct award"
    ],
    
    # Supplier-driven specification / biased requirements (Mantzaris p.7-8)
    "Biased specifications / tailored requirements": [
        "specification", "specifications", "brand specific", "brand-specific", 
        "must be", "only acceptable", "tailored", "preferred supplier", 
        "oem required", "no alternatives", "equivalent not accepted",
        "proprietary", "custom made", "unique requirement"
    ],
    
    # Information asymmetry / insider information (Mantzaris p.5)
    "Information asymmetry / insider advantage": [
        "confidential information", "insider", "privileged", "non-public",
        "asymmetric information", "inside track", "advance notice",
        "early warning", "heads up", "private briefing"
    ],
    
    # Evaluation manipulation / biased scoring (Mantzaris p.5)
    "Evaluation manipulation / biased scoring": [
        "evaluation", "score", "scoring", "points", "adjudication", "award", 
        "preferred bidder", "preferred supplier", "disqualify", "eliminate", 
        "technicality", "non-responsive", "responsive bid", "weighting",
        "criteria", "assessment panel", "evaluation committee"
    ],
    
    # Bid rigging / collusion (Mantzaris p.5)
    "Bid rigging / collusion": [
        "collusion", "collusive", "cover pricing", "cover bid", "complementary bid",
        "rotating wins", "take turns", "bid rotation", "market allocation",
        "territory allocation", "customer allocation", "bid suppression",
        "bid withdrawal", "phantom bid", "courtesy bid"
    ],
    
    # Contract variation / scope creep (Mantzaris p.8-9)
    "Contract variation / scope creep": [
        "variation", "extension", "extend", "amendment", "scope change", 
        "change order", "price increase", "addendum", "renewal", "rate increase", 
        "escalation", "additional work", "supplementary", "variation order",
        "contract modification", "renegotiation"
    ],
    
    # Invoice / payment fraud (Mantzaris p.9)
    "Invoice / payment fraud": [
        "invoice", "payment", "pay", "remit", "proof of delivery", "pod", 
        "delivery note", "goods received", "grn", "not delivered", 
        "no delivery note", "overcharge", "duplicate invoice", "credit note", 
        "advance payment", "prepayment", "false claim", "inflated invoice",
        "ghost delivery", "non-delivery", "short delivery"
    ],
    
    # Supplier master / bank detail change risk (Common fraud vector)
    "Supplier bank detail change fraud": [
        "bank details", "banking details", "account change", "change banking", 
        "new bank account", "update banking", "beneficiary change", 
        "change beneficiary", "proof of bank", "bank confirmation letter",
        "iban change", "swift change", "payment instruction update"
    ],
    
    # Conflict of interest (Mantzaris p.5, p.9-10)
    "Conflict of interest": [
        "conflict of interest", "coi", "family member", "relative", "brother", 
        "sister", "cousin", "spouse", "wife", "husband", "son", "daughter",
        "friend owns", "relationship", "kickback", "bribe", "commission", 
        "gift", "hospitality", "sponsorship", "undue influence",
        "personal interest", "financial interest", "shareholder"
    ],
    
    # Segregation of duties failure (Mantzaris p.9)
    "Segregation of duties failure": [
        "override", "approve and pay", "no approval", "bypass approval", 
        "direct approval", "same person", "system admin", "password shared", 
        "shared password", "superuser", "sole control", "single approver",
        "no separation", "incompatible functions"
    ],
    
    # Threshold splitting / fragmentation (Mantzaris p.8)
    "Threshold splitting / fragmentation": [
        "split order", "split purchase", "multiple orders", "divide order",
        "fragmented", "below threshold", "just below", "under the limit",
        "separate invoices", "partial delivery", "phased approach"
    ],
    
    # Shell company indicators (Mantzaris p.10)
    "Shell company indicators": [
        "po box", "post box", "private bag", "registered address",
        "newly registered", "recently registered", "just incorporated",
        "dormant", "inactive", "no physical address", "virtual office",
        "shared address", "same address as", "common director"
    ],
    
    # Poor quality / substandard goods (Mantzaris p.8)
    "Substandard goods/services": [
        "poor quality", "substandard", "defective", "not as specified",
        "different brand", "substitute", "alternative product", "second hand",
        "used", "refurbished", "reconditioned", "grey market", "counterfeit",
        "fake", "imitation", "non-compliant", "failed specification"
    ],
    
    # Missing documentation (Auditor-General report p.9)
    "Missing/incomplete documentation": [
        "missing documents", "no documentation", "incomplete file",
        "cannot locate", "lost file", "no records", "not filed",
        "documentation not available", "cannot provide"
    ]
}

# PFMA references based on Section 38 (Mantzaris p.2)
PFMA_SECTIONS = {
    "s38(1)(a)(iii)": "Accounting officer must maintain appropriate procurement system that is fair, equitable, transparent, competitive and cost-effective",
    "s38(1)(c)(ii)": "Effective, efficient and transparent systems of financial and risk management",
    "s38(1)(h)": "Ensure expenditure complies with PFMA and is within budget",
    "s81": "Financial misconduct - fruitless and wasteful, irregular expenditure",
    "s83": "Disciplinary proceedings for financial misconduct"
}

TREASURY_REGULATIONS = {
    "TR 16A3.1": "SCM system must be fair, equitable, transparent, competitive and cost-effective",
    "TR 16A3.2": "Threshold values for procurement methods",
    "TR 16A6.1": "Bid documentation and specifications",
    "TR 16A6.3": "Bid evaluation and award criteria",
    "TR 16A6.4": "Bid committee composition and functioning",
    "TR 16A7.1": "Contract management and performance monitoring",
    "TR 16A8.3": "Supply chain management register",
    "TR 16A9": "Unacceptable conduct and blacklisting"
}

# Risk scoring weights based on Mantzaris severity indicators
RISK_WEIGHTS = {
    "Critical": 5,  # Immediate red flags: collusion, kickbacks, false invoices
    "High": 4,       # Serious concerns: single source, urgency, biased specs
    "Medium": 3,     # Notable issues: limited competition, poor documentation
    "Low": 1,        # Minor concerns: administrative issues
    "None": 0
}

# FALSE POSITIVE REDUCTION ADDITIONS

# Add negation patterns to reduce false positives
NEGATION_PATTERNS = [
    r'\bnot\s+(\w+)',
    r'\bno\s+(\w+)',
    r'\bwithout\s+(\w+)',
    r'\bexcept\s+(\w+)',
    r'\bexcluding\s+(\w+)',
    r'\bavoid\s+(\w+)',
    r'\bprevent\s+(\w+)',
    r'\bno evidence of\s+(\w+)',
    r'\bno indication of\s+(\w+)',
]

# Common false positive words/phrases to ignore
FALSE_POSITIVE_IGNORE = {
    "urgent": ["not urgent", "no urgency", "without urgency", "avoid urgency"],
    "emergency": ["not an emergency", "no emergency", "without emergency"],
    "rush": ["not a rush", "no rush", "without rush"],
    "conflict": ["no conflict", "without conflict", "resolve conflict"],
    "single supplier": ["no single supplier", "avoid single supplier"],
    "sole source": ["no sole source", "avoid sole source"],
    "delegated": ["properly delegated", "appropriately delegated"],
}

# Business context patterns that are normal (not fraud)
NORMAL_BUSINESS_PATTERNS = [
    # Standard procurement language
    r'\bstandard (?:procurement|purchasing|ordering)\b',
    r'\bnormal (?:process|procedure|practice)\b',
    r'\broutine (?:order|purchase|procurement)\b',
    r'\bregular (?:supplier|vendor|contractor)\b',
    
    # Compliance language
    r'\bin accordance with (?:policy|regulation|procedure)\b',
    r'\bcompliant with (?:PFMA|Treasury|regulation)\b',
    r'\bfollowing (?:standard|normal) procedure\b',
    r'\bproper (?:authorization|approval|documentation)\b',
    
    # Mitigation language
    r'\bmitigation (?:measure|strategy|plan)\b',
    r'\bcontrol (?:measure|procedure|mechanism)\b',
    r'\breviewed (?:and|by) (?:approved|authorized)\b',
]

# Low-risk organizational roles that shouldn't trigger agent conflict
LOW_RISK_ROLES = {
    'assistant', 'coordinator', 'officer', 'clerk', 'specialist',
    'analyst', 'administrator', 'consultant', 'advisor', 'manager',
    'director', 'head', 'chief', 'supervisor', 'team lead'
}

def _norm(text: str) -> str:
    """Normalize text for matching"""
    return re.sub(r"\s+", " ", (text or "")).lower().strip()

def _has_negation(text: str, keyword: str, window: int = 30) -> bool:
    """Check if keyword is negated within context window"""
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Find all occurrences of the keyword
    for match in re.finditer(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
        start = max(0, match.start() - window)
        end = min(len(text_lower), match.end() + window)
        context = text_lower[start:end]
        
        # Check for negation patterns
        for pattern in NEGATION_PATTERNS:
            if re.search(pattern, context):
                # Verify it's actually negating this keyword
                words_before = context[:match.start() - start].split()
                if words_before and words_before[-1] in ['not', 'no', 'without', 'except', 'excluding', 'avoid', 'prevent']:
                    return True
    
    return False

def _is_normal_business_context(text: str) -> bool:
    """Check if text indicates normal business operations"""
    text_lower = text.lower()
    for pattern in NORMAL_BUSINESS_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

def _needs_context_specific_handling(text: str, indicator_name: str) -> bool:
    """Determine if indicator needs special handling based on context"""
    text_lower = text.lower()
    
    # Handle urgency indicators
    if "urgency" in indicator_name.lower():
        # Check if it's genuine urgency vs. standard business language
        if re.search(r'\b(?:asap|urgent|immediate|emergency)\b.*\b(?:due to|because of|as a result of)\b', text_lower):
            return True  # Genuine urgency with reason
        if re.search(r'\b(?:deadline|timeline|schedule)\b', text_lower):
            return False  # Normal deadline discussion
    
    # Handle conflict of interest
    if "conflict" in indicator_name.lower():
        # Check if it's about resolving conflict vs. having conflict
        if re.search(r'\b(?:resolve|avoid|prevent|manage)\s+conflict\b', text_lower):
            return False
        # Check if it's about organizational roles
        if re.search(r'\b(?:role|responsibility|duty)\b.*\b(?:conflict)\b', text_lower):
            return False
    
    # Handle single supplier
    if "single supplier" in indicator_name.lower():
        # Check if it's justified
        if re.search(r'\b(?:only|unique|specialized|proprietary)\b.*\b(?:supplier|vendor)\b', text_lower):
            # Check for justification language
            if re.search(r'\b(?:because|due to|as|since)\b', text_lower[:100]):
                return False  # Likely justified
    
    return True

def detect_indicators(text: str, min_confidence: float = 0.6) -> List[Tuple[str, List[str], float]]:
    """
    Enhanced detection with false positive reduction
    Returns indicator name, matched keywords, and confidence score
    """
    t = _norm(text)
    hits: List[Tuple[str, List[str], float]] = []
    
    # Skip if it's normal business context
    if _is_normal_business_context(t):
        return []
    
    # Track keyword frequencies to avoid single occurrences
    keyword_counter = Counter()
    
    for name, keywords in INDICATOR_KEYWORDS.items():
        matched = []
        confidence_factors = []
        
        for keyword in keywords:
            # Skip if keyword is negated
            if _has_negation(t, keyword):
                continue
                
            # Check if keyword appears
            if keyword in t:
                matched.append(keyword)
                keyword_counter[keyword] += 1
                
                # Calculate confidence based on various factors
                confidence = 0.5  # Base confidence
                
                # Higher confidence for exact matches
                if re.search(r'\b' + re.escape(keyword) + r'\b', t):
                    confidence += 0.2
                
                # Higher confidence for multiple occurrences
                if keyword_counter[keyword] >= 2:
                    confidence += 0.2
                
                # Check context-specific handling
                if _needs_context_specific_handling(t, name):
                    confidence += 0.1
                
                confidence_factors.append(confidence)
        
        # Only include if we have matches and average confidence above threshold
        if matched:
            avg_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.3
            if avg_confidence >= min_confidence:
                hits.append((name, matched, avg_confidence))
    
    return hits

def infer_stage(text: str) -> str:
    """
    Map content to procurement stage with false positive reduction
    """
    t = _norm(text)
    
    # Skip if it's normal business context
    if _is_normal_business_context(t):
        return "Not procurement-related"
    
    # Require at least 2 matches for stage inference to avoid false positives
    stage_matches = {}
    
    # Order & Payment stage
    order_keywords = ["invoice", "payment", "remit", "grn", "goods received",
                     "proof of delivery", "pod", "delivery note", "bank details", 
                     "beneficiary", "settlement", "pay", "paid"]
    order_score = sum(2 for k in order_keywords if k in t)  # Weight 2 for payment terms
    if order_score >= 4:  # At least 2 matches
        stage_matches["Order & Payment"] = order_score
    
    # Post-award/Contract Management
    post_keywords = ["variation", "extension", "amendment", "change order",
                    "addendum", "scope change", "renewal", "additional work",
                    "contract management", "performance", "monitoring"]
    post_score = sum(1 for k in post_keywords if k in t)
    if post_score >= 3:
        stage_matches["Post-award/Contract Mgmt"] = post_score
    
    # Evaluation & Award
    eval_keywords = ["award", "adjudication", "preferred bidder", "evaluation",
                    "score", "points", "non-responsive", "responsive",
                    "winning bid", "successful bidder", "recommended"]
    eval_score = sum(1 for k in eval_keywords if k in t)
    if eval_score >= 3:
        stage_matches["Evaluation & Award"] = eval_score
    
    # Tendering stage
    tender_keywords = ["tender", "bid", "rfq", "rfx", "quotation", "closing date",
                      "briefing session", "bid submission", "proposal",
                      "invitation to bid", "call for bids"]
    tender_score = sum(1 for k in tender_keywords if k in t)
    if tender_score >= 3:
        stage_matches["Tendering"] = tender_score
    
    # Specifications/Requirements
    spec_keywords = ["specification", "specifications", "requirements", 
                    "brand specific", "brand-specific", "oem required", 
                    "equivalent not accepted", "terms of reference",
                    "tor", "technical requirements"]
    spec_score = sum(1 for k in spec_keywords if k in t)
    if spec_score >= 3:
        stage_matches["Specs/Requirements"] = spec_score
    
    # Procedure Choice
    proc_keywords = ["deviation", "sole source", "single supplier", 
                    "restricted tender", "limited quotations", 
                    "limited quotes", "negotiated procedure",
                    "competitive bidding", "open tender"]
    proc_score = sum(1 for k in proc_keywords if k in t)
    if proc_score >= 2:
        stage_matches["Procedure Choice"] = proc_score
    
    # Pre-tender/Planning
    pre_keywords = ["budget", "planning", "needs assessment", "motivation", 
                   "business case", "procurement plan", "feasibility",
                   "market research", "cost estimate"]
    pre_score = sum(1 for k in pre_keywords if k in t)
    if pre_score >= 3:
        stage_matches["Pre-tender/Planning"] = pre_score
    
    if stage_matches:
        # Return the stage with highest score
        return max(stage_matches.items(), key=lambda x: x[1])[0]
    
    return "Not procurement-related"

def calculate_risk_score(indicators: List[Tuple[str, List[str], float]], stage: str) -> Tuple[int, str]:
    """
    Calculate numeric risk score and rating based on weighted indicators
    Based on Auditor-General risk categories (p.9-10)
    """
    score = 0
    indicator_names = [i[0] for i in indicators]
    
    # High-risk indicators (Critical - weight 5)
    critical_indicators = [
        "Bid rigging / collusion",
        "Conflict of interest",
        "Invoice / payment fraud",
        "Supplier bank detail change fraud"
    ]
    
    # Medium-high indicators (High - weight 4)
    high_indicators = [
        "Reduced competition / single supplier",
        "Biased specifications / tailored requirements",
        "Urgency / emergency procurement pressure",
        "Contract variation / scope creep",
        "Evaluation manipulation / biased scoring"
    ]
    
    # Medium indicators (Medium - weight 3)
    medium_indicators = [
        "Information asymmetry / insider advantage",
        "Segregation of duties failure",
        "Threshold splitting / fragmentation",
        "Shell company indicators"
    ]
    
    # Low indicators (Low - weight 1)
    low_indicators = [
        "Principal/agent conflict",
        "Substandard goods/services",
        "Missing/incomplete documentation"
    ]
    
    for ind in indicator_names:
        if ind in critical_indicators:
            score += 5
        elif ind in high_indicators:
            score += 4
        elif ind in medium_indicators:
            score += 3
        elif ind in low_indicators:
            score += 1
    
    # Additional risk based on stage
    stage_risk = {
        "Evaluation & Award": 2,
        "Order & Payment": 2,
        "Post-award/Contract Mgmt": 1,
        "Tendering": 1
    }
    score += stage_risk.get(stage, 0)
    
    # Determine rating
    if score >= 10:
        rating = "Critical"
    elif score >= 7:
        rating = "High"
    elif score >= 4:
        rating = "Medium"
    elif score >= 1:
        rating = "Low"
    else:
        rating = "Low"
    
    return score, rating

def extract_financial_data(text: str) -> Dict:
    """
    Extract financial information for fraud analysis
    """
    # Find currency amounts (R, $, €, £)
    amounts = re.findall(r'[R$€£]\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)', text)
    
    # Find numbers that look like amounts (with thousand separators)
    number_amounts = re.findall(r'\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d{2})?\b', text)
    
    all_amounts = amounts + number_amounts
    
    # Convert to numeric values
    numeric_amounts = []
    for amt in all_amounts:
        # Remove commas and spaces
        amt_clean = amt.replace(',', '').replace(' ', '')
        try:
            numeric_amounts.append(float(amt_clean))
        except:
            pass
    
    # Find invoice numbers
    invoice_numbers = re.findall(r'(?:invoice|inv)[\s#]*([A-Z0-9-]+)', text, re.IGNORECASE)
    
    # Find order numbers
    order_numbers = re.findall(r'(?:order|po|p\.?o\.?)[\s#]*([A-Z0-9-]+)', text, re.IGNORECASE)
    
    return {
        "amounts_found": all_amounts,
        "numeric_amounts": numeric_amounts,
        "total_mentioned": sum(numeric_amounts) if numeric_amounts else 0,
        "avg_amount": sum(numeric_amounts)/len(numeric_amounts) if numeric_amounts else 0,
        "high_value": max(numeric_amounts) if numeric_amounts else 0,
        "invoice_numbers": invoice_numbers,
        "order_numbers": order_numbers,
        "has_financial_data": len(numeric_amounts) > 0
    }

def detect_threshold_issues(amounts: List[float], text: str = "") -> List[str]:
    """
    Detect potential threshold splitting with false positive reduction
    """
    issues = []
    thresholds = [
        (100000, "R100,000"),  # Below tender threshold
        (500000, "R500,000"),  # Competitive bidding threshold
        (2000000, "R2,000,000")  # High-value threshold
    ]
    
    # Skip if no amounts or if it's clearly a single large procurement
    if not amounts or len(amounts) == 1:
        return []
    
    # Look for justification language that would explain multiple amounts
    text_lower = text.lower()
    justification_patterns = [
        r'\b(?:phased|staged|milestone)\s+(?:approach|delivery|payment)\b',
        r'\b(?:multiple|separate)\s+(?:deliveries|shipments|batches)\b',
        r'\b(?:over|spanning|covering)\s+(?:period|duration|timeframe)\b',
        r'\b(?:annual|monthly|quarterly)\s+(?:contract|agreement|order)\b',
    ]
    
    has_justification = any(re.search(pattern, text_lower) for pattern in justification_patterns)
    
    # Group amounts by size and date proximity (simplified here)
    for amt in amounts:
        for threshold, desc in thresholds:
            # Check if amount is suspiciously close to threshold
            if amt < threshold and amt > threshold * 0.9:
                # Don't flag if we have justification
                if has_justification:
                    continue
                
                # Don't flag very small amounts
                if amt < 10000:
                    continue
                
                # Check if this is part of a pattern
                similar_amounts = [a for a in amounts if abs(a - amt) < threshold * 0.05]
                if len(similar_amounts) >= 2:
                    issues.append(f"Multiple amounts (n={len(similar_amounts)}) just below {desc} threshold - potential splitting")
                else:
                    issues.append(f"Amount R{amt:,.0f} is just below {desc} threshold")
                break
    
    return list(set(issues))  # Remove duplicates

def deterministic_procurement_assessment(text: str) -> Dict:
    """
    Enhanced deterministic SCM risk assessment with false positive reduction
    """
    # Early exit for clearly non-procurement content
    procurement_keywords = ['procurement', 'purchase', 'order', 'supplier', 'vendor', 
                           'contract', 'tender', 'bid', 'invoice', 'payment']
    if not any(kw in text.lower() for kw in procurement_keywords):
        return {
            "risk_rating": "Low",
            "risk_score": 0,
            "scm_stage": "Not procurement-related",
            "risk_indicators": [],
            "matched_keywords": {},
            "indicator_confidence": {},
            "procurement_risk_reason": "Not procurement-related based on available content.",
            "financial_indicators": extract_financial_data(text),
            "threshold_issues": [],
            "pfma_refs": [],
            "treasury_reg_refs": [],
            "policy_clause_refs": [],
        }
    
    # Get indicators with confidence scores
    indicators_with_confidence = detect_indicators(text)
    indicators = [(name, matched) for name, matched, conf in indicators_with_confidence]
    
    stage = infer_stage(text)
    risk_score, rating = calculate_risk_score(indicators_with_confidence, stage)
    
    # Only calculate financial data if there's substantial content
    financial_data = extract_financial_data(text)
    threshold_issues = detect_threshold_issues(financial_data['numeric_amounts'], text)
    
    # Build risk reason with confidence levels
    if indicators:
        indicator_names = [i[0] for i in indicators]
        matched_keywords = {i[0]: i[1] for i in indicators}
        
        # Get confidence info for the reason
        conf_info = []
        for name, _, conf in indicators_with_confidence:
            conf_level = "High" if conf >= 0.8 else "Medium" if conf >= 0.6 else "Low"
            conf_info.append(f"{name} ({conf_level} confidence)")
        
        reason = f"{stage} - Risk rating {rating} ({risk_score} points). "
        reason += f"Key indicators: {', '.join(conf_info[:3])}."
        
        if threshold_issues:
            reason += f" Threshold concerns: {'; '.join(threshold_issues)}."
        if financial_data['high_value'] > 100000:  # Only mention high values
            reason += f" Highest amount: R{financial_data['high_value']:,.0f}."
    else:
        reason = f"{stage} - No specific risk indicators identified."
    
    # Map to PFMA/Treasury references based on indicators and confidence
    pfma_refs = []
    treasury_refs = []
    
    if stage != "Not procurement-related" and indicators:
        # Only add references for medium-high confidence indicators
        high_conf_indicators = [name for name, _, conf in indicators_with_confidence if conf >= 0.7]
        
        if high_conf_indicators:
            pfma_refs = ["PFMA s38(1)(a)(iii) - Fair, equitable, transparent, competitive procurement"]
            treasury_refs = ["TR 16A3.1 - SCM system requirements"]
            
            if "Conflict of interest" in high_conf_indicators:
                pfma_refs.append("PFMA s38(1)(h) - Ensure compliance, prevent unauthorized expenditure")
                treasury_refs.append("TR 16A8.3 - SCM register and disclosure of interests")
            
            if "Bid rigging / collusion" in high_conf_indicators:
                treasury_refs.append("TR 16A9 - Unacceptable conduct and blacklisting")
            
            if "Invoice / payment fraud" in high_conf_indicators:
                pfma_refs.append("PFMA s81 - Financial misconduct")
                treasury_refs.append("TR 16A7.1 - Contract performance monitoring")
    
    return {
        "risk_rating": rating,
        "risk_score": risk_score,
        "scm_stage": stage,
        "risk_indicators": [i[0] for i in indicators[:5]],
        "matched_keywords": {i[0]: i[1] for i in indicators},
        "indicator_confidence": {name: conf for name, _, conf in indicators_with_confidence},
        "procurement_risk_reason": reason,
        "financial_indicators": financial_data,
        "threshold_issues": threshold_issues,
        "pfma_refs": list(set(pfma_refs)),
        "treasury_reg_refs": list(set(treasury_refs)),
        "policy_clause_refs": [
            "Bid committee controls",
            "Approvals & Segregation of Duties",
            "Supplier onboarding verification",
            "3-way match (PO/GRN/Invoice)",
            "Contract variation approvals",
            "Threshold compliance monitoring"
        ] if indicators else [],
    }

def llm_procurement_prompt(system_instructions: str, email_summary: str, attachment_summaries: str) -> str:
    """
    Enhanced LLM prompt for procurement risk assessment
    """
    return f"""{system_instructions}

You are a forensic procurement fraud expert analyzing emails for potential corruption based on the Mantzaris research framework.

Assess procurement / supply chain management (SCM) risks. Only use facts present in the summaries. Do not invent.

Consider these specific fraud indicators from the Mantzaris paper:
- Bid rigging / collusion (cover pricing, bid rotation)
- Conflict of interest (family relationships, undisclosed interests)
- Threshold splitting (purchases just below tender limits)
- Urgency/emergency bypassing normal processes
- Biased specifications favoring specific suppliers
- Information asymmetry/insider advantage
- Contract variations and scope creep
- Invoice fraud (duplicate, inflated, false claims)
- Shell company indicators (PO boxes, recent registration)

IMPORTANT: Avoid false positives. Only flag indicators if there is clear evidence. Consider context and look for justification language that might explain normal business practices.

Return ONLY valid JSON with exactly these keys:
{{
  "risk_rating": "Low|Medium|High|Critical",
  "risk_score": <numeric 0-20>,
  "scm_stage": "Pre-tender/Planning|Specs/Requirements|Procedure Choice|Tendering|Evaluation & Award|Post-award/Contract Mgmt|Order & Payment|Not procurement-related",
  "risk_indicators": ["specific indicator 1", "specific indicator 2"],
  "procurement_risk_reason": "2-3 sentences explaining the specific risks identified",
  "suspected_fraud_types": ["collusion", "conflict_of_interest", "invoice_fraud", etc],
  "pfma_refs": ["PFMA sections violated"],
  "treasury_reg_refs": ["Treasury regulations potentially breached"],
  "policy_clause_refs": ["Internal controls that should have caught this"]
}}

EMAIL SUMMARY
{email_summary or "Not stated."}

ATTACHMENT SUMMARIES
{attachment_summaries or "None."}
"""