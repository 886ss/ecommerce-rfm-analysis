"""
E-Commerce Data Analysis Project - Main Entry Point
UCI Online Retail Dataset
Focus: RFM Segmentation + Funnel Attribution + CLV Estimation
"""
import sys
from pathlib import Path

SRC = Path(__file__).parent
sys.path.insert(0, str(SRC))

DATA = str(SRC.parent / "data" / "Online Retail.xlsx")
OUT = str(SRC.parent / "output")

from rfm_analysis import run_rfm
from funnel_attribution import run_funnel
from clv_estimation import run_clv


def main():
    print("=" * 60)
    print("  E-Commerce Data Analysis: RFM + Funnel + CLV")
    print("  Dataset: UCI Online Retail")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("  STEP 1/3: RFM Customer Segmentation")
    print("=" * 60)
    rfm, rfm_summary = run_rfm(DATA, OUT)

    print("\n" + "=" * 60)
    print("  STEP 2/3: Funnel Attribution Analysis")
    print("=" * 60)
    funnel, insights = run_funnel(DATA, OUT)

    print("\n" + "=" * 60)
    print("  STEP 3/3: Customer Lifetime Value Estimation")
    print("=" * 60)
    clv, clv_summary = run_clv(DATA, OUT)

    print("\n" + "=" * 60)
    print("  ALL ANALYSES COMPLETE")
    print(f"  Output files in: {OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
