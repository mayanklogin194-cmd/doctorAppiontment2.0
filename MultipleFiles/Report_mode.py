# MultipleFiles/Report_mode.py (Modified)
import pdfplumber
import re
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

# Code to import the pdf and read it and save the data in text variable and return it
def extract_text_from_pdf(file_path): # Changed 'file' to 'file_path' for clarity
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# This will extract the values from the text variable
def extract_medical_values(text):
    values = {}
    patterns = {
        "Heart Rate": r"Heart Rate.*?(\d+)",
        "Hemoglobin": r"Hemoglobin.*?([\d.]+)",
        "Blood Sugar": r"(Blood Sugar|Glucose).*?([\d.]+)",
        "Platelet Count": r"Platelet.*?([\d,]+)",
        "WBC Count": r"(WBC|White Blood Cell).*?([\d,]+)",
        "RBC Count": r"(RBC|Red Blood Cell).*?([\d.]+)",
        "Cholesterol": r"Cholesterol.*?([\d.]+)",
        "Blood Pressure": r"Blood Pressure.*?(\d+/\d+)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(2) if "|" in pattern else match.group(1)
            value = value.replace(",", "")
            if "/" in value:
                values[key] = value
            elif "." in value:
                values[key] = float(value)
            else:
                values[key] = int(value)
    return values

# Health status
def check_health_simple(values):
    status_dict = {}
    # Removed print statements, now just return the dict
    # ... (keep the logic as is, but remove prints)
    if "Hemoglobin" in values:
        try:
            h = values["Hemoglobin"]
            if h < 13.5: status_dict["Hemoglobin"] = "Low"
            elif h > 17.5: status_dict["Hemoglobin"] = "High"
            else: status_dict["Hemoglobin"] = "Normal"
        except: status_dict["Hemoglobin"] = "Could not analyze"

    if "Blood Sugar" in values:
        try:
            bs = values["Blood Sugar"]
            if bs < 70: status_dict["Blood Sugar"] = "Low"
            elif bs > 99: status_dict["Blood Sugar"] = "High"
            else: status_dict["Blood Sugar"] = "Normal"
        except: status_dict["Blood Sugar"] = "Could not analyze"

    if "WBC Count" in values:
        try:
            wbc = values["WBC Count"]
            if wbc < 999: wbc *= 1000
            if wbc < 4000: status_dict["WBC Count"] = "Low"
            elif wbc > 11000: status_dict["WBC Count"] = "High"
            else: status_dict["WBC Count"] = "Normal"
        except: status_dict["WBC Count"] = "Could not analyze"

    if "RBC Count" in values:
        try:
            rbc = values["RBC Count"]
            if rbc < 4.5: status_dict["RBC Count"] = "Low"
            elif rbc > 5.9: status_dict["RBC Count"] = "High"
            else: status_dict["RBC Count"] = "Normal"
        except: status_dict["RBC Count"] = "Could not analyze"

    if "Platelet Count" in values:
        try:
            plt_count = values["Platelet Count"]
            if plt_count < 999: plt_count *= 1000
            if plt_count < 150000: status_dict["Platelet Count"] = "Low"
            elif plt_count > 450000: status_dict["Platelet Count"] = "High"
            else: status_dict["Platelet Count"] = "Normal"
        except: status_dict["Platelet Count"] = "Could not analyze"

    if "Heart Rate" in values:
        try:
            hr = values["Heart Rate"]
            if hr < 60: status_dict["Heart Rate"] = "Low"
            elif hr > 100: status_dict["Heart Rate"] = "High"
            else: status_dict["Heart Rate"] = "Normal"
        except: status_dict["Heart Rate"] = "Could not analyze"

    if "Cholesterol" in values:
        try:
            chol = values["Cholesterol"]
            if chol < 200: status_dict["Cholesterol"] = "Normal"
            else: status_dict["Cholesterol"] = "High"
        except: status_dict["Cholesterol"] = "Could not analyze"

    if "Blood Pressure" in values:
        try:
            bp = values["Blood Pressure"]
            sys, dia = map(int, bp.split("/"))
            if sys < 90 or dia < 60: status_dict["Blood Pressure"] = "Low"
            elif sys > 120 or dia > 80: status_dict["Blood Pressure"] = "High"
            else: status_dict["Blood Pressure"] = "Normal"
        except: status_dict["Blood Pressure"] = "Could not analyze"

    return status_dict

# Function to generate and return base64 encoded image for bar chart
def generate_bar_chart(values, status_dict):
    normal_ranges = {
        "Hemoglobin": (13.5, 17.5), "Blood Sugar": (70, 99), "WBC Count": (4000, 11000),
        "RBC Count": (4.5, 5.9), "Platelet Count": (150000, 450000), "Heart Rate": (60, 100),
        "Cholesterol": (0, 200),
    }
    labels, extracted, standard = [], [], []

    for key, status in status_dict.items():
        if key in values:
            val = values[key]
            if key == "Blood Pressure" and isinstance(val, str):
                try:
                    sys, dia = map(int, val.split("/"))
                    val = (sys + dia) / 2
                    standard_val, min_val, max_val = 100, 60, 180
                except: continue
            else:
                if key == "WBC Count" and val < 999: val *= 1000
                if key == "Platelet Count" and val < 999: val *= 1000
                low, high = normal_ranges.get(key, (0, 1))
                standard_val = (low + high) / 2
                min_val, max_val = low, high

            try:
                norm_extracted = (val - min_val) / (max_val - min_val)
                norm_standard = (standard_val - min_val) / (max_val - min_val)
            except ZeroDivisionError:
                norm_extracted, norm_standard = 0.5, 0.5

            labels.append(key)
            extracted.append(norm_extracted)
            standard.append(norm_standard)

    plt.figure(figsize=(10, 5))
    x = range(len(labels))
    width = 0.35
    plt.bar([i - width / 2 for i in x], extracted, width=width, label='Extracted ', color='green')
    plt.bar([i + width / 2 for i in x], standard, width=width, label='Standard ', color='blue')
    plt.xticks(x, labels, rotation=45)
    plt.ylabel("Normalized Value (0 to 1)")
    plt.title("📊 Normalized Extracted vs Standard Health Values")
    plt.legend()
    plt.tight_layout()

    # Save plot to a BytesIO object and encode to base64
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close() # Close the plot to free memory
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Function to generate and return base64 encoded image for pie chart
def generate_pie_chart(status_dict):
    count = {"Low": 0, "Normal": 0, "High": 0}
    for status in status_dict.values(): # Iterate over values directly
        if status in count:
            count[status] += 1

    plt.figure(figsize=(4, 4))
    plt.pie(
        list(count.values()),
        labels=list(count.keys()),
        colors=["orange", "green", "red"],
        autopct="%1.1f%%",
        startangle=90
    )
    plt.title("🩺 Health Status Summary")
    plt.tight_layout()

    # Save plot to a BytesIO object and encode to base64
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close() # Close the plot to free memory
    return base64.b64encode(buf.getvalue()).decode('utf-8')

import base64
from io import BytesIO

import os
import matplotlib.pyplot as plt
from datetime import datetime

def plot_health_ring(metric_name, value, status, min_val, max_val, save_dir):
    """Plots a dual-ring chart for a single health metric and saves as PNG in static/tmp."""
    outer_sizes = [100]
    outer_colors = ["#ecf0f1"]

    percentage = min((value / max_val) * 100, 100)

    if min_val <= value <= max_val:
        color = "#2ecc71"  # green
    elif value < min_val:
        color = "#3498db"  # blue for low
    else:
        color = "#e74c3c"  # red for high

    inner_sizes = [percentage, 100 - percentage]
    inner_colors = [color, "#ffffff"]

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(outer_sizes, radius=1, colors=outer_colors,
           wedgeprops=dict(width=0.3, edgecolor='white'))
    ax.pie(inner_sizes, radius=0.85, colors=inner_colors, startangle=90,
           wedgeprops=dict(width=0.3, edgecolor='white'))
    plt.text(0, 0, f"{metric_name}\n{value} ({status})",
             ha='center', va='center', fontsize=10, weight='bold')
    ax.axis('equal')

    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{metric_name.lower().replace(' ', '_')}_{timestamp}.png"
    filepath = os.path.join(save_dir, filename)

    plt.savefig(filepath, format='png')
    plt.close(fig)

    return filename


def generate_ring_charts(values, status_dict):
    """Generates PNG ring charts for all metrics and returns list of filenames."""
    normal_ranges = {
        "Hemoglobin": (13.5, 17.5),
        "Blood Sugar": (70, 99),
        "WBC Count": (4000, 11000),
        "RBC Count": (4.5, 5.9),
        "Platelet Count": (150000, 450000),
        "Heart Rate": (60, 100),
        "Cholesterol": (0, 200),
        "Blood Pressure": (60, 180)
    }

    charts = []
    static_tmp_dir = os.path.join("static", "tmp")

    for key, status in status_dict.items():
        if key in values:
            val = values[key]
            if key == "Blood Pressure":
                sys, dia = map(int, val.split("/"))
                val = (sys + dia) / 2
            if key in ["WBC Count", "Platelet Count"] and val < 999:
                val *= 1000

            min_val, max_val = normal_ranges[key]
            filename = plot_health_ring(key, val, status, min_val, max_val, static_tmp_dir)
            charts.append({"name": key, "path": filename})

    return charts



# The main report_mode function will no longer be called directly by Flask
def report_mode():
    pass
