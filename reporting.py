import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def create_summary_string(swimmer, race_details, data):
    """
    Build a summary string with all metrics.
    """
    lines = []
    lines.append(f"Swimmer: {swimmer}")
    lines.append(f"Race Details: {race_details}")
    lines.append("")
    lines.append("Race Metrics:")
    if data.get("total_time") is not None:
        lines.append(f"  Total Race Time: {data['total_time']:.2f} seconds")
    if data.get("water_entry_time") is not None:
        lines.append(f"  Water Entry Time: {data['water_entry_time']:.2f} seconds")
    if data.get("fifteen_time") is not None:
        lines.append(f"  15m Time: {data['fifteen_time']:.2f} seconds")
    # Breakout events
    if data.get("breakouts"):
        for i, b in enumerate(data["breakouts"], start=1):
            distance = b.get("extra", {}).get("distance", 0)
            lines.append(f"  Breakout {i}: Time = {b['time']:.2f} s, Distance = {distance} m")
        if data.get("avg_breakout_time") is not None:
            lines.append(f"  Avg Breakout Time: {data['avg_breakout_time']:.2f} seconds")
        if data.get("avg_breakout_distance") is not None:
            lines.append(f"  Avg Breakout Distance: {data['avg_breakout_distance']:.2f} m")
    # Turn events and lap times
    if data.get("turns"):
        for i, t in enumerate(data["turns"], start=1):
            lines.append(f"  Lap {i} Turn Time: {t['lap_time']:.2f} seconds "
                         f"(Start: {t['start']:.2f}, End: {t['end']:.2f})")
        if data.get("avg_turn_time") is not None:
            lines.append(f"  Avg Turn Time: {data['avg_turn_time']:.2f} seconds")
    # Underwater times
    if data.get("underwater_times"):
        for i, ut in enumerate(data["underwater_times"], start=1):
            lines.append(f"  Lap {i} Underwater Time: {ut:.2f} seconds")
        if data.get("avg_underwater_time") is not None:
            lines.append(f"  Avg Underwater Time: {data['avg_underwater_time']:.2f} seconds")
    # Stroke info
    if data.get("strokes"):
        lines.append(f"  Total Strokes: {len(data['strokes'])}")
    if data.get("avg_stroke_interval") is not None:
        lines.append(f"  Avg Stroke Interval: {data['avg_stroke_interval']:.2f} seconds")
    if data.get("manual_stroke_counts"):
        counts_str = ", ".join(map(str, data["manual_stroke_counts"]))
        lines.append(f"  Manual Stroke Counts per Lap: {counts_str}")
        if data.get("avg_manual_stroke_count") is not None:
            lines.append(f"  Avg Stroke Count per Lap: {data['avg_manual_stroke_count']:.2f}")
    return "\n".join(lines)

def print_summary(swimmer, race_details, data):
    """
    Print the summary of race metrics.
    """
    summary = create_summary_string(swimmer, race_details, data)
    print("\n" + "="*40)
    print("Race Summary")
    print("="*40)
    print(summary)

def generate_pdf_report(swimmer, race_details, data):
    """
    Generate a PDF report with three pages:
     1. Summary text
     2. Stroke intervals graph (tempo)
     3. Bar chart for manual stroke counts per lap (if provided)
    """
    pdf_filename = f"{swimmer.replace(' ', '_')}_race_report.pdf"
    with PdfPages(pdf_filename) as pdf:
        # Page 1: Summary text
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 size in inches
        ax.axis("off")
        summary_str = create_summary_string(swimmer, race_details, data)
        ax.text(0.05, 0.95, summary_str, va="top", fontsize=10, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: Stroke Intervals (Tempo)
        if data.get("stroke_intervals"):
            fig2, ax2 = plt.subplots()
            x = range(1, len(data["stroke_intervals"]) + 1)
            ax2.plot(x, data["stroke_intervals"], marker="o")
            ax2.set_title("Stroke Intervals (Tempo)")
            ax2.set_xlabel("Interval Number")
            ax2.set_ylabel("Time between strokes (sec)")
            pdf.savefig(fig2)
            plt.close(fig2)

        # Page 3: Manual Stroke Counts per Lap, if provided
        if data.get("manual_stroke_counts") and len(data["manual_stroke_counts"]) > 0:
            fig3, ax3 = plt.subplots()
            laps = range(1, len(data["manual_stroke_counts"]) + 1)
            ax3.bar(laps, data["manual_stroke_counts"])
            ax3.set_title("Stroke Count per Lap")
            ax3.set_xlabel("Lap")
            ax3.set_ylabel("Stroke Count")
            pdf.savefig(fig3)
            plt.close(fig3)
    print(f"\nPDF report generated: {pdf_filename}") 