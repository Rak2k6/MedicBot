import re
import json
import os
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Constants
VALID_UNITS = {
    "mg/dl", "g/dl", "g/l", "mg/l", "µg/dl", "ng/ml", "pg/ml", "u/l", "iu/l", "u/ml",
    "%", "/µl", "/mm3", "cells/cumm", "cells/ul", "cells/µl", "millions/cumm", "lakhs/cumm",
    "fl", "pg", "ratio", "mg/24hr", "mmol/l", "meq/l", "g/24h", "mg/g", "µg/mg", "ul", "hpf", "lpf"
}

# Add lowercase versions
VALID_UNITS = {u.lower() for u in VALID_UNITS}

UNIT_CORRECTIONS = {
    "mg/d|": "mg/dl",
    "g/d|": "g/dl",
    "9": "%", 
    "/u|": "/ul",
    "u|": "ul",
    "|u/l": "iu/l",
    "|u": "iu",
    "0/0": "%",
}

# Medical Context Whitelist
MEDICAL_KEYWORDS = {
    "blood", "urine", "stool", "glucose", "protein", "cells", "rbc", "wbc", "ph", 
    "ketone", "bilirubin", "urobilinogen", "nitrite", "bacteria", "haemoglobin", 
    "hemoglobin", "count", "platelet", "albumin", "globulin", "test", "result",
    "differential", "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"
}

# Physical Examination Attributes
COMMON_LAB_ATTRIBUTES = {
    "color", "appearance", "clarity", "consistency", "odour", "specific gravity", "ph", "reaction"
}

# Administrative Keywords (for filtering and validation)
ADMIN_KEYWORDS = {
    "reg date", "report date", "sid", "branch", "page", "referrer", "referred",
    "patient name", "name:", "age", "sex", "gender", "uhid", "bill no", "sample id",
    "accession", "reg no", "barcode", "end of report", "accredited", "nabl", "iso",
    "visit date", "collected on", "received on", "registered on", "dr.", "doctor",
    "consultant", "signature", "technologist", "pathologist", "radiologist"
}

# Qualitative Clinical Values
VALID_NON_NUMERIC_VALUES = {
    "nil", "negative", "absent", "trace", "present", "not seen", "reactive", 
    "non-reactive", "positive", "normal", "abnormal", "yellow", "straw", "clear",
    "cloudy", "pale", "amber", "dark", "hazy", "semi-solid", "formed"
}

# Regex Patterns
DATE_PATTERN = r'\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b'
TIME_PATTERN = r'\b\d{1,2}[:.]\d{2}(?::\d{2})?\b'
# Range patterns: 0-5, 4.5 - 5.5, <0.5, >100
RANGE_PATTERN = r'([<>]?\s*\d*\.?\d+\s*(?:-|to)\s*[<>]?\s*\d*\.?\d+)'
VALUE_PATTERN = r'([<>=]?\s*[-+]?\d*\.?\d+)'


class LayoutParser:
    """
    Refactored Stage-2 Layout-Aware Parser using Coordinate-Based Spatial Logic.
    """
    
    def __init__(self, rules_path: str = None):
        self.test_names_map = self._load_test_names(rules_path)
        
    def _load_test_names(self, rules_path: str) -> Dict[str, List[str]]:
        if not rules_path:
            rules_path = os.path.join(os.path.dirname(__file__), '..', 'rules', 'test_names.json')
        try:
            if os.path.exists(rules_path):
                with open(rules_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load test names in LayoutParser: {e}")
        return {}

    def normalize_term(self, term: str) -> str:
        if not term: return ""
        term_upper = term.upper().strip()
        for _, variations in self.test_names_map.items():
            for variation in variations:
                if term_upper == variation.upper():
                    return variations[0]
        return term

    def convert_to_unified_format(self, raw_output: Any, source: str) -> List[Dict[str, Any]]:
        unified_tokens = []
        max_y = 0
        
        if source == "easyocr":
            for item in raw_output:
                box, text, conf = item["box"], item["text"], item["confidence"]
                x_min, y_min = min(p[0] for p in box), min(p[1] for p in box)
                x_max, y_max = max(p[0] for p in box), max(p[1] for p in box)
                h = y_max - y_min
                max_y = max(max_y, y_min + h)
                unified_tokens.append({
                    "text": text, "x": x_min, "y": y_min, "w": x_max - x_min, "h": h, "conf": conf
                })
        elif source == "pdfplumber":
            for word in raw_output:
                h = word["bottom"] - word["top"]
                max_y = max(max_y, word["top"] + h)
                unified_tokens.append({
                    "text": word["text"], "x": word["x0"], "y": word["top"], 
                    "w": word["x1"] - word["x0"], "h": h, "conf": 1.0
                })
        
        # Tag Zones and Admin Noise
        top_zone = max_y * 0.15
        bottom_zone = max_y * 0.85
        
        for t in unified_tokens:
            text_lower = t["text"].lower()
            t["in_zone"] = "header" if t["y"] < top_zone else ("footer" if t["y"] > bottom_zone else "body")
            
            # Identify Admin/Header attributes
            t["is_admin"] = any(ak in text_lower for ak in ADMIN_KEYWORDS)
            
            # Pattern-based rejection (Dates/Times in header/footer)
            if t["in_zone"] != "body":
                if re.search(DATE_PATTERN, text_lower) or re.search(TIME_PATTERN, text_lower):
                    t["is_admin"] = True
                    
        return unified_tokens

    def _calculate_dynamic_metrics(self, tokens: List[Dict[str, Any]]) -> Tuple[float, float, float]:
        if not tokens:
            return 10.0, 5.0, 1000.0
        heights = sorted([t['h'] for t in tokens])
        widths = sorted([t['w'] / max(1, len(t['text'])) for t in tokens])
        dyn_h = float(heights[min(len(heights)//2, len(heights)-1)])
        dyn_w = float(widths[min(len(widths)//2, len(widths)-1)])
        max_y = max(t["y"] + t["h"] for t in tokens)
        return dyn_h, dyn_w, max_y

    def _detect_columns(self, tokens: List[Dict[str, Any]], dyn_w: float) -> List[List[Dict[str, Any]]]:
        # Sort tokens by x center to group them
        sorted_tokens = sorted(tokens, key=lambda t: t["x"] + t["w"]/2.0)
        columns = []
        
        for t in sorted_tokens:
            placed = False
            for col in columns:
                col_min_x = min(ct["x"] for ct in col)
                col_max_x = max(ct["x"] + ct["w"] for ct in col)
                # Group if overlapping or close
                if t["x"] <= col_max_x + 2 * dyn_w and (t["x"] + t["w"]) >= col_min_x - 2 * dyn_w:
                    col.append(t)
                    placed = True
                    break
            if not placed:
                columns.append([t])
        
        # Merge columns that are too close (secondary pass)
        # Using 3.0 * dyn_w as a heuristic for column separation
        if len(columns) > 1:
            columns.sort(key=lambda col: sum(ct["x"]+ct["w"]/2 for ct in col) / len(col))
            merged_cols = [columns[0]]
            for i in range(1, len(columns)):
                prev_col = merged_cols[-1]
                curr_col = columns[i]
                prev_avg_x = sum(ct["x"]+ct["w"]/2 for ct in prev_col) / len(prev_col)
                curr_avg_x = sum(ct["x"]+ct["w"]/2 for ct in curr_col) / len(curr_col)
                if abs(curr_avg_x - prev_avg_x) < 5.0 * dyn_w:
                    prev_col.extend(curr_col)
                else:
                    merged_cols.append(curr_col)
            columns = merged_cols

        # Final Sort
        for col in columns:
            col.sort(key=lambda t: t["y"])
        columns.sort(key=lambda col: sum(ct["x"]+ct["w"]/2 for ct in col) / len(col))
        return columns

    def _extract_val_inline_unit(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts value, inline unit, and potential reference range.
        Returns: (value, unit, range)
        """
        text = text.strip()
        text_lower = text.lower()
        
        # 0. Reject Dates and Times from being treated as Values
        if re.search(DATE_PATTERN, text) or re.search(TIME_PATTERN, text):
            return None, None, None
            
        # 1. Qualitative Clinical Values (Non-numeric)
        for qv in VALID_NON_NUMERIC_VALUES:
            if qv in text_lower:
                # Check for unit after the qualitative word
                remainder = text_lower.replace(qv, "").strip()
                unit = remainder if remainder in VALID_UNITS else None
                return qv, unit, None
        
        # 2. Reference Range Detection (MANDATORY)
        range_match = re.search(RANGE_PATTERN, text)
        if range_match:
            # If the whole text is a range (e.g., "0 - 5"), it's not a value
            # But if it's "13.5 (12.0 - 15.0)", we extract value and range.
            range_str = range_match.group(1).strip()
            # Remove range from text to find value
            text_without_range = text.replace(range_str, "").strip()
            val, unit = self._extract_numeric_value_and_unit(text_without_range)
            return val, unit, range_str

        # 3. Standard Numeric Value + Unit
        val, unit = self._extract_numeric_value_and_unit(text)
        return val, unit, None

    def _extract_numeric_value_and_unit(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        text = re.sub(r'[:\|]', '', text).strip()
        
        # Reject Large Numeric IDs (e.g. > 10000) as values unless small or specific
        # Exceptions: Hemoglobin 14.5 is fine, but SID 1234567 is noise.
        m = re.match(VALUE_PATTERN, text)
        if m:
            val_str = m.group(1).strip()
            # Large ID protection
            try:
                num_val = float(val_str.replace('<', '').replace('>', ''))
                if num_val > 10000:
                    return None, None
            except ValueError:
                pass
                
            remainder = text.replace(m.group(1), "").strip()
            unit_str = remainder if remainder.lower().strip() in VALID_UNITS else None
            return val_str, unit_str
            
        return None, None

    def _is_value_only(self, text: str) -> bool:
        v, _, _ = self._extract_val_inline_unit(text)
        return v is not None

    def _is_likely_unit(self, text: str) -> bool:
        if not text: return False
        text = text.lower().strip()
        if text in UNIT_CORRECTIONS: return True
        for u in VALID_UNITS:
            if u in text: return True
        return False

    def _normalize_unit(self, text: str) -> Optional[str]:
        if not text: return None
        text_lower = text.lower().strip()
        for wrong, right in UNIT_CORRECTIONS.items():
            if text_lower == wrong:
                return right
        return text_lower

    def _is_valid_test_name(self, name: str) -> bool:
        if not name or len(name.split()) > 8:
            return False
        
        name_lower = name.lower()
        # Reject repeated words (e.g., "CHENNAI CHENNAI")
        words = name_lower.split()
        if len(words) >= 2 and len(set(words)) == 1:
            return False
            
        # Reject administrative text
        if any(ak in name_lower for ak in ADMIN_KEYWORDS):
            return False
            
        return True

    def _has_medical_context(self, val_token: Dict, test_name: Optional[str], unit: Optional[str], columns: List[List[Dict]], dyn_h: float, dyn_w: float) -> bool:
        """
        Implements the Medical Context Rule:
        Accept if: has_unit OR has_medical_keyword OR is_common_attribute
        """
        # 1. Valid Unit is already a strong indicator
        if unit and unit.lower() in VALID_UNITS:
            return True
        
        # 2. Check for Medical Keywords or Common Attributes
        combined_context = (test_name or "").lower()
        if any(mk in combined_context for mk in MEDICAL_KEYWORDS) or \
           any(ca in combined_context for ca in COMMON_LAB_ATTRIBUTES):
            return True
            
        # 3. Spatial Context Detection (X and Y Axis)
        for col in columns:
            for t in col:
                y_dist = abs(t["y"] - val_token["y"])
                x_dist = abs(t["x"] - val_token["x"])
                if y_dist < 2.0 * dyn_h and x_dist < 15 * dyn_w:
                    text_lower = t["text"].lower()
                    if any(mk in text_lower for mk in MEDICAL_KEYWORDS) or \
                       any(ca in text_lower for ca in COMMON_LAB_ATTRIBUTES):
                        return True
                        
        return False

    def _calculate_entry_score(self, res: Dict, val_token: Dict, proximity: float, dyn_h: float) -> float:
        """
        Step 8: Confidence Scoring (Point System)
        Adaptive: qualitative/attribute results get specific weight logic to survive zone penalties.
        """
        score = 0.0
        val_lower = res.get("value", "").lower()
        name_lower = (res.get("test_name") or "").lower()
        
        # 1. Base Scores (User Points)
        if res.get("unit"): score += 0.4
        is_med = any(mk in name_lower for mk in MEDICAL_KEYWORDS)
        is_attr = any(ca in name_lower for ca in COMMON_LAB_ATTRIBUTES)
        
        if is_med or is_attr: 
            score += 0.3
        
        # 2. Adaptive Qualitative/Attribute Bonus
        # Qualitative results and basic attributes need extra weight to survive zone penalties
        if val_lower in VALID_NON_NUMERIC_VALUES or is_attr:
            score += 0.2
            
        # 3. Proximity Bonus (User Rule: +0.2)
        # Lenient limit for qualitative/attribute matches
        prox_limit = 0.8 * dyn_h if (val_lower in VALID_NON_NUMERIC_VALUES or is_attr) else 0.4 * dyn_h
        if proximity <= prox_limit:
            score += 0.2
            
        # 4. Zone Penalty (User Rule: -0.3)
        if val_token.get("in_zone") != "body":
            score -= 0.3
            
        return round(score, 2)

    def _find_unit_or_range(self, val_token: Dict, inline_unit: Optional[str], inline_range: Optional[str], columns: List[List[Dict]], col_idx: int, dyn_h: float, dyn_w: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Finds unit and reference range, supporting adjacent/disjointed detection.
        """
        unit = self._normalize_unit(inline_unit) if inline_unit and self._is_likely_unit(inline_unit) else None
        ref_range = inline_range
        
        if unit and ref_range:
            return unit, ref_range
            
        # Adjacent Search (Right or Below) for missing pieces
        for idx in range(col_idx, min(col_idx + 2, len(columns))):
            for t in columns[idx]:
                if t == val_token: continue
                y_dist = abs(t["y"] - val_token["y"])
                x_dist = t["x"] - (val_token["x"] + val_token["w"])
                
                # Spatial bounds for adjacent detection
                if y_dist <= 2.5 * dyn_h and -5 * dyn_w <= x_dist <= 15 * dyn_w:
                    text = t["text"]
                    # Range Detection
                    if not ref_range:
                        range_match = re.search(RANGE_PATTERN, text)
                        if range_match:
                            ref_range = range_match.group(1).strip()
                    # Unit Detection
                    if not unit and self._is_likely_unit(text):
                        unit = self._normalize_unit(text)
                        
        return unit, ref_range

    def _group_by_x_gap(self, tokens: List[Dict], gap_threshold: float) -> List[List[Dict]]:
        if not tokens: return []
        sorted_t = sorted(tokens, key=lambda t: t["x"])
        clusters = [[sorted_t[0]]]
        for t in sorted_t[1:]:
            prev = clusters[-1][-1]
            gap = t["x"] - (prev["x"] + prev["w"])
            if gap <= gap_threshold:
                clusters[-1].append(t)
            else:
                clusters.append([t])
        return clusters

    def _find_test_name(self, val_token: Dict, columns: List[List[Dict]], col_idx: int, dyn_h: float, dyn_w: float, is_qualitative: bool = False) -> Tuple[Optional[str], float]:
        """
        Search Left for the nearest test name.
        SafeGuard: strict Y-drift (0.6 dyn_h) and column-aware.
        Adaptive: qualitative results allow slightly higher drift (1.2 dyn_h).
        """
        y_limit = 1.2 * dyn_h if is_qualitative else 0.6 * dyn_h
        
        for idx in range(col_idx, -1, -1):
            candidates = []
            for t in columns[idx]:
                if t == val_token: continue
                # Must be to the left (Left-Only mapping safeguard)
                if t["x"] + t["w"] < val_token["x"]:
                    y_dist = abs(t["y"] - val_token["y"])
                    if y_dist <= y_limit:
                        candidates.append((t, y_dist))
                        
            if candidates:
                # Rank candidates by Y-distance primarily
                candidates.sort(key=lambda x: x[1])
                
                # Filter pure numbers (might be previous column's value)
                text_cands = [c for c in candidates if not self._is_value_only(c[0]["text"])]
                if not text_cands: continue
                
                # Safeguard: full test name reconstruction. 
                # Cluster them by X-gap.
                best_token, best_y_dist = text_cands[0]
                clusters = self._group_by_x_gap([c[0] for c in text_cands], gap_threshold=6.0 * dyn_w)
                
                # Grab the cluster containing our best Y-match
                best_cluster = next(c for c in clusters if best_token in c)
                best_cluster.sort(key=lambda t: t["x"])
                
                name_parts = [t["text"] for t in best_cluster]
                name = " ".join(name_parts)
                name = re.sub(r'[:\|]', '', name).strip()
                
                if len(name) > 1:
                    return name, best_y_dist
                    
        return None, 100.0

    def group_rows(self, tokens: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Legacy support: Groups tokens into rows based on Y-axis proximity.
        Uses dynamic horizontal metrics for thresholding.
        """
        if not tokens: return []
        dyn_h, _, _ = self._calculate_dynamic_metrics(tokens)
        threshold = dyn_h * 0.8
        
        sorted_tokens = sorted(tokens, key=lambda t: (t["y"], t["x"]))
        rows = []
        current_row = [sorted_tokens[0]]
        
        for i in range(1, len(sorted_tokens)):
            token = sorted_tokens[i]
            avg_y = sum(t["y"] for t in current_row) / len(current_row)
            if abs(token["y"] - avg_y) <= threshold:
                current_row.append(token)
            else:
                rows.append(current_row)
                current_row = [token]
        rows.append(current_row)
        return rows

    def parse_document_spatial(self, unified_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main pipeline using Spatial & Context Filtering.
        """
        if not unified_tokens: return []
        
        dyn_h, dyn_w, _ = self._calculate_dynamic_metrics(unified_tokens)
        columns = self._detect_columns(unified_tokens, dyn_w)
        
        results_list = []
        
        for col_idx, col in enumerate(columns):
            for t in col:
                # 1. Soft Zone & Admin Filtering
                if t.get("is_admin") or (t.get("in_zone") != "body" and t.get("conf", 0) < 0.6):
                    continue
                    
                val, inline_unit, inline_range = self._extract_val_inline_unit(t["text"])
                
                if val:
                    # 2. Adjacent Unit & Range Detection
                    unit, ref_range = self._find_unit_or_range(t, inline_unit, inline_range, columns, col_idx, dyn_h, dyn_w)
                    
                    # 3. Test Name Association & Validation (Left-Only, Column-Aware, Adaptive)
                    is_qual = val.lower() in VALID_NON_NUMERIC_VALUES
                    test_name, y_drift = self._find_test_name(t, columns, col_idx, dyn_h, dyn_w, is_qualitative=is_qual)
                    
                    # 4. Context Layer & Confidence Scoring
                    if test_name and self._is_valid_test_name(test_name):
                        if self._has_medical_context(t, test_name, unit, columns, dyn_h, dyn_w):
                            entry = {
                                "test_name": self.normalize_term(test_name),
                                "value": val,
                                "unit": unit,
                                "reference_range": ref_range
                            }
                            # Step 8: Confidence Scoring
                            score = self._calculate_entry_score(entry, t, y_drift, dyn_h)
                            
                            if score >= 0.4:
                                entry["confidence"] = score
                                results_list.append(entry)
                        
        return results_list

    def parse_document(self, unified_tokens: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Main pipeline adapter that returns the legacy Dict format with range support.
        """
        list_results = self.parse_document_spatial(unified_tokens)
        structured_data = {}
        for item in list_results:
            key = item["test_name"]
            structured_data[key] = {
                "value": item["value"],
                "unit": item["unit"],
                "reference_range": item.get("reference_range")
            }
        return structured_data


def parse_lab_tests_layout_aware(tokens_source: List[Dict[str, Any]], source_type: str) -> Dict[str, Any]:
    """
    Adapter function mapping the new spatial output back to the
    historical Dict format required by the current integration.
    """
    parser = LayoutParser()
    unified = parser.convert_to_unified_format(tokens_source, source_type)
    return parser.parse_document(unified)
