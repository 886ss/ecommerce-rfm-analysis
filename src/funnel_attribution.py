"""
Funnel Attribution Analysis: Maps customer journey from first purchase
through repeat purchase to high-value status, identifying drop-off points.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from data_preprocessing import load_and_clean


FUNNEL_STAGES = [
    ("Total Customers", "Made at least 1 purchase"),
    ("Repeat Buyers", "Made 2+ purchases"),
    ("Regular Buyers", "Made 5+ purchases"),
    ("High-Value Buyers", "Top 20% by total spend"),
    ("VIP Buyers", "Top 5% by total spend"),
]


def build_funnel(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Build purchase-based conversion funnel."""
    cust = cleaned_df.groupby("CustomerID").agg(
        Total_Spend=("Revenue", "sum"),
        Purchase_Count=("InvoiceNo", "nunique"),
    )

    total = len(cust)

    stages = []
    for name, _ in FUNNEL_STAGES:
        if name == "Total Customers":
            count = total
        elif name == "Repeat Buyers":
            count = (cust["Purchase_Count"] >= 2).sum()
        elif name == "Regular Buyers":
            count = (cust["Purchase_Count"] >= 5).sum()
        elif name == "High-Value Buyers":
            threshold = cust["Total_Spend"].quantile(0.80)
            count = (cust["Total_Spend"] >= threshold).sum()
        elif name == "VIP Buyers":
            threshold = cust["Total_Spend"].quantile(0.95)
            count = (cust["Total_Spend"] >= threshold).sum()
        else:
            count = 0

        pct = count / total * 100
        stages.append({"Stage": name, "Customers": count, "Pct_of_Total": round(pct, 1)})

    funnel_df = pd.DataFrame(stages)

    # Calculate conversion rates between adjacent stages
    conv_rates = []
    for i in range(len(funnel_df)):
        if i == 0:
            conv_rates.append(100.0)
        else:
            prev = funnel_df.iloc[i - 1]["Customers"]
            curr = funnel_df.iloc[i]["Customers"]
            conv_rates.append(round(curr / prev * 100, 1) if prev > 0 else 0)
    funnel_df["Stage_Conversion"] = conv_rates

    return funnel_df


def analyze_dropoff(funnel_df: pd.DataFrame) -> dict:
    """Identify the largest drop-off points in the funnel."""
    insights = {}
    for i in range(1, len(funnel_df)):
        stage_name = funnel_df.iloc[i]["Stage"]
        drop = 100 - funnel_df.iloc[i]["Stage_Conversion"]
        insights[stage_name] = {
            "from": funnel_df.iloc[i - 1]["Stage"],
            "to": stage_name,
            "conversion": funnel_df.iloc[i]["Stage_Conversion"],
            "dropoff": round(drop, 1),
            "lost_customers": int(funnel_df.iloc[i - 1]["Customers"] - funnel_df.iloc[i]["Customers"]),
        }
    return insights


def plot_funnel(funnel_df: pd.DataFrame, output_dir: str):
    """Draw funnel chart and drop-off bar chart."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Funnel chart (horizontal bars, reversed to look like a funnel)
    stages = funnel_df["Stage"].tolist()[::-1]
    counts = funnel_df["Customers"].tolist()[::-1]
    colors = ["#2ecc71", "#3498db", "#f39c12", "#e74c3c", "#9b59b6"][::-1]

    axes[0].barh(stages, counts, color=colors, edgecolor="white", height=0.6)
    axes[0].set_xlabel("Number of Customers", fontsize=11)
    axes[0].set_title("Customer Funnel", fontsize=13, fontweight="bold")
    for i, (s, c) in enumerate(zip(stages, counts)):
        pct = funnel_df.iloc[::-1].iloc[i]["Pct_of_Total"]
        axes[0].text(c + max(counts) * 0.01, i, f"{c:,} ({pct}%)", va="center", fontsize=9)

    # Drop-off rates
    drop_labels = []
    drop_vals = []
    for i in range(1, len(funnel_df)):
        label = f"{funnel_df.iloc[i-1]['Stage']}\n-> {funnel_df.iloc[i]['Stage']}"
        drop_labels.append(label)
        drop_vals.append(100 - funnel_df.iloc[i]["Stage_Conversion"])

    bar_colors = ["#e74c3c" if v > 50 else "#f39c12" if v > 30 else "#3498db" for v in drop_vals]
    axes[1].barh(drop_labels, drop_vals, color=bar_colors, edgecolor="white", height=0.5)
    axes[1].set_xlabel("Drop-off Rate (%)", fontsize=11)
    axes[1].set_title("Funnel Drop-off Analysis", fontsize=13, fontweight="bold")
    for i, v in enumerate(drop_vals):
        axes[1].text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9, fontweight="bold")
    axes[1].set_xlim(0, max(drop_vals) * 1.3)

    plt.tight_layout()
    path = str(Path(output_dir) / "funnel_attribution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Funnel] Chart saved: {path}")


def run_funnel(data_path: str, output_dir: str):
    df = load_and_clean(data_path)
    funnel = build_funnel(df)

    print("\n[Funnel] Attribution Results:")
    print(funnel.to_string(index=False))

    insights = analyze_dropoff(funnel)
    print("\n[Funnel] Key Drop-off Points:")
    for stage, info in insights.items():
        print(f"  {info['from']} -> {info['to']}: {info['conversion']}% retained, "
              f"{info['dropoff']}% dropped ({info['lost_customers']:,} customers)")

    plot_funnel(funnel, output_dir)

    funnel_path = Path(output_dir) / "funnel_table.csv"
    funnel.to_csv(funnel_path, index=False)
    print(f"[Funnel] Table saved: {funnel_path}")

    return funnel, insights


if __name__ == "__main__":
    DATA = str(Path(__file__).parent.parent / "data" / "Online Retail.xlsx")
    OUT = str(Path(__file__).parent.parent / "output")
    run_funnel(DATA, OUT)
