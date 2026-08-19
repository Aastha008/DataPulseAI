import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, Optional

class StatisticalEngine:
    @staticmethod
    def calculate_ab_test(
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Calculates two-proportion z-test, p-value, relative lift, and confidence intervals."""
        if control_total <= 0 or treatment_total <= 0:
            return {"error": "Sample sizes must be greater than zero."}
            
        p_c = control_conversions / control_total
        p_t = treatment_conversions / treatment_total
        
        # Absolute difference and relative lift
        abs_diff = p_t - p_c
        rel_lift_pct = (abs_diff / p_c * 100.0) if p_c > 0 else 0.0
        
        # Pooled probability for z-test
        p_pool = (control_conversions + treatment_conversions) / (control_total + treatment_total)
        se_pool = np.sqrt(p_pool * (1 - p_pool) * (1/control_total + 1/treatment_total))
        
        if se_pool == 0:
            z_score = 0.0
            p_value = 1.0
        else:
            z_score = abs_diff / se_pool
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
        # Confidence interval on difference
        alpha = 1.0 - confidence_level
        z_crit = stats.norm.ppf(1 - alpha/2)
        se_diff = np.sqrt((p_c * (1 - p_c) / control_total) + (p_t * (1 - p_t) / treatment_total))
        
        ci_lower = abs_diff - z_crit * se_diff
        ci_upper = abs_diff + z_crit * se_diff
        
        is_significant = p_value < alpha
        
        return {
            "control": {
                "conversions": int(control_conversions),
                "total": int(control_total),
                "conversion_rate": round(float(p_c), 4),
                "conversion_rate_pct": round(float(p_c * 100), 2)
            },
            "treatment": {
                "conversions": int(treatment_conversions),
                "total": int(treatment_total),
                "conversion_rate": round(float(p_t), 4),
                "conversion_rate_pct": round(float(p_t * 100), 2)
            },
            "relative_lift_pct": round(float(rel_lift_pct), 2),
            "absolute_difference": round(float(abs_diff), 4),
            "z_score": round(float(z_score), 4),
            "p_value": float(p_value),
            "confidence_level": confidence_level,
            "confidence_interval_95": [round(float(ci_lower * 100), 2), round(float(ci_upper * 100), 2)],
            "statistically_significant": bool(is_significant),
            "recommendation": "Launch Treatment (Statistically Significant Lift)" if is_significant and rel_lift_pct > 0 else (
                "Do Not Launch (Statistically Significant Drop)" if is_significant and rel_lift_pct < 0 else "Inconclusive (No Significant Difference)"
            )
        }

    @staticmethod
    def check_sample_ratio_mismatch(
        control_count: int,
        treatment_count: int,
        expected_ratio: float = 0.5,
        alpha: float = 0.01
    ) -> Dict[str, Any]:
        """Chi-square goodness-of-fit test to detect Sample Ratio Mismatch (SRM) traffic allocation bias."""
        total = control_count + treatment_count
        if total <= 0:
            return {"srm_detected": False, "error": "Total count is zero."}
            
        expected_control = total * expected_ratio
        expected_treatment = total * (1.0 - expected_ratio)
        
        chi2_stat, p_value = stats.chisquare(
            f_obs=[control_count, treatment_count],
            f_exp=[expected_control, expected_treatment]
        )
        
        has_srm = p_value < alpha
        
        return {
            "control_observed": int(control_count),
            "treatment_observed": int(treatment_count),
            "total_observed": int(total),
            "actual_control_ratio": round(float(control_count / total), 4),
            "expected_control_ratio": expected_ratio,
            "chi2_statistic": round(float(chi2_stat), 4),
            "p_value": float(p_value),
            "srm_detected": bool(has_srm),
            "status": "CRITICAL SRM DETECTED (Traffic allocation corrupted! Experiment results invalid)" if has_srm else "Normal Allocation (No SRM detected)"
        }

    @staticmethod
    def calculate_funnel(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates stage-by-stage drop-off from event dataframe."""
        stages = ["view_item", "add_to_cart", "start_checkout", "purchase"]
        counts = {}
        for s in stages:
            if "event_type" in df.columns:
                counts[s] = int((df["event_type"] == s).sum())
            elif s in df.columns:
                counts[s] = int(df[s].sum())
            else:
                counts[s] = 0
                
        dropoffs = {}
        prev_count = None
        for s in stages:
            c = counts[s]
            if prev_count is not None and prev_count > 0:
                conv_rate = (c / prev_count) * 100.0
                drop_rate = 100.0 - conv_rate
                dropoffs[s] = {
                    "count": c,
                    "conversion_from_prev_pct": round(conv_rate, 2),
                    "dropoff_pct": round(drop_rate, 2)
                }
            else:
                dropoffs[s] = {
                    "count": c,
                    "conversion_from_prev_pct": 100.0,
                    "dropoff_pct": 0.0
                }
            prev_count = c
            
        return {
            "funnel_counts": counts,
            "stage_metrics": dropoffs,
            "overall_conversion_pct": round((counts["purchase"] / counts["view_item"] * 100.0), 2) if counts["view_item"] > 0 else 0.0
        }

stats_engine = StatisticalEngine()
