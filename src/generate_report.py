#!/usr/bin/env python3
"""
Generate interactive HTML report from LSTV uncertainty analysis
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import json
import base64
from jinja2 import Template
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LSTV Uncertainty Analysis Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        
        .stat-card h3 {
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: 700;
            color: #2d3748;
        }
        
        .stat-card .label {
            color: #718096;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .section {
            padding: 40px;
        }
        
        .section-title {
            font-size: 1.8em;
            color: #2d3748;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        
        .plot-container {
            margin: 30px 0;
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        th, td {
            padding: 15px;
            text-align: left;
        }
        
        th {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        
        tbody tr {
            border-bottom: 1px solid #e2e8f0;
            transition: background 0.2s ease;
        }
        
        tbody tr:hover {
            background: #f7fafc;
        }
        
        tbody tr:last-child {
            border-bottom: none;
        }
        
        .lstv-high {
            background: #fed7d7;
            color: #c53030;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        
        .lstv-medium {
            background: #feebc8;
            color: #c05621;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        
        .lstv-low {
            background: #c6f6d5;
            color: #276749;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        
        .methodology {
            background: #edf2f7;
            padding: 30px;
            border-radius: 15px;
            margin: 30px 0;
        }
        
        .methodology h3 {
            color: #2d3748;
            margin-bottom: 15px;
        }
        
        .methodology p {
            line-height: 1.8;
            color: #4a5568;
        }
        
        .footer {
            background: #2d3748;
            color: white;
            padding: 30px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 LSTV Uncertainty Analysis</h1>
            <p>Epistemic Uncertainty-Based LSTV Detection</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Using Ian Pan's RSNA 2024 Spine Localizer</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Studies</h3>
                <div class="value">{{ stats.total_studies }}</div>
                <div class="label">Analyzed</div>
            </div>
            <div class="stat-card">
                <h3>High Uncertainty</h3>
                <div class="value">{{ stats.high_uncertainty }}</div>
                <div class="label">L5/S1 Entropy > 5.0</div>
            </div>
            <div class="stat-card">
                <h3>Detection Rate</h3>
                <div class="value">{{ stats.detection_rate }}%</div>
                <div class="label">Potential LSTV Cases</div>
            </div>
            <div class="stat-card">
                <h3>Mean L5-S1 Entropy</h3>
                <div class="value">{{ stats.mean_l5_s1_entropy }}</div>
                <div class="label">Shannon Entropy</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 Distribution Analysis</h2>
            
            <div class="methodology">
                <h3>Methodology</h3>
                <p>
                    <strong>Hypothesis:</strong> A spine localizer trained on normal anatomy will exhibit high epistemic 
                    uncertainty (confusion) when encountering LSTV anomalies. We measure this using Shannon entropy 
                    of the probability heatmaps.
                </p>
                <p style="margin-top: 10px;">
                    <strong>Metrics:</strong> Peak Confidence (max probability), Entropy (H = -Σp log p), 
                    and Spatial Entropy (spatial distribution of probability mass).
                </p>
            </div>
            
            <div class="plot-container">
                {{ entropy_distribution_plot }}
            </div>
            
            <div class="plot-container">
                {{ confidence_distribution_plot }}
            </div>
            
            <div class="plot-container">
                {{ scatter_plot }}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🎯 Top LSTV Candidates</h2>
            <p style="margin-bottom: 20px; color: #4a5568;">
                Studies ranked by L5-S1 uncertainty (highest first). High entropy indicates potential LSTV.
            </p>
            
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Study ID</th>
                        <th>L5-S1 Entropy</th>
                        <th>L5-S1 Confidence</th>
                        <th>L4-L5 Entropy</th>
                        <th>Risk Level</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in top_candidates %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td><strong>{{ row.study_id }}</strong></td>
                        <td>{{ "%.4f"|format(row.l5_s1_entropy) }}</td>
                        <td>{{ "%.4f"|format(row.l5_s1_confidence) }}</td>
                        <td>{{ "%.4f"|format(row.l4_l5_entropy) }}</td>
                        <td><span class="{{ row.risk_class }}">{{ row.risk_label }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 Level-by-Level Comparison</h2>
            <div class="plot-container">
                {{ level_comparison_plot }}
            </div>
        </div>
        
        {% if debug_images %}
        <div class="section">
            <h2 class="section-title">🔍 Debug Visualizations</h2>
            {% for img_data in debug_images %}
            <div class="plot-container">
                <h3>{{ img_data.title }}</h3>
                <img src="data:image/png;base64,{{ img_data.base64 }}" style="max-width: 100%; border-radius: 10px;">
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Generated by LSTV Uncertainty Analysis Pipeline</p>
            <p style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;">
                Wayne State University School of Medicine | {{ timestamp }}
            </p>
        </div>
    </div>
</body>
</html>
"""


def create_entropy_distribution_plot(df: pd.DataFrame) -> str:
    """Create distribution plot for entropy across all levels"""
    
    fig = make_subplots(
        rows=1, cols=5,
        subplot_titles=['L1-L2', 'L2-L3', 'L3-L4', 'L4-L5', 'L5-S1']
    )
    
    levels = ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']
    colors = ['#4299e1', '#48bb78', '#ed8936', '#f56565', '#9f7aea']
    
    for idx, (level, color) in enumerate(zip(levels, colors), 1):
        entropy_col = f'{level}_entropy'
        
        fig.add_trace(
            go.Histogram(
                x=df[entropy_col],
                name=level.upper(),
                marker_color=color,
                opacity=0.7,
                nbinsx=30
            ),
            row=1, col=idx
        )
    
    fig.update_layout(
        title_text="Entropy Distribution by Vertebral Level",
        showlegend=False,
        height=400,
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Entropy")
    fig.update_yaxes(title_text="Count")
    
    return fig.to_html(include_plotlyjs=False, div_id="entropy_dist")


def create_confidence_distribution_plot(df: pd.DataFrame) -> str:
    """Create distribution plot for confidence across all levels"""
    
    levels = ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']
    colors = ['#4299e1', '#48bb78', '#ed8936', '#f56565', '#9f7aea']
    
    fig = go.Figure()
    
    for level, color in zip(levels, colors):
        conf_col = f'{level}_confidence'
        
        fig.add_trace(go.Box(
            y=df[conf_col],
            name=level.upper().replace('_', '-'),
            marker_color=color,
            boxmean='sd'
        ))
    
    fig.update_layout(
        title_text="Peak Confidence Distribution by Level",
        yaxis_title="Peak Confidence",
        template='plotly_white',
        height=500
    )
    
    return fig.to_html(include_plotlyjs=False, div_id="confidence_dist")


def create_scatter_plot(df: pd.DataFrame) -> str:
    """Create scatter plot of entropy vs confidence for L5-S1"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['l5_s1_confidence'],
        y=df['l5_s1_entropy'],
        mode='markers',
        marker=dict(
            size=10,
            color=df['l5_s1_entropy'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Entropy"),
            line=dict(width=1, color='white')
        ),
        text=df['study_id'],
        hovertemplate='<b>Study:</b> %{text}<br>' +
                     '<b>Confidence:</b> %{x:.4f}<br>' +
                     '<b>Entropy:</b> %{y:.4f}<extra></extra>'
    ))
    
    # Add threshold lines
    fig.add_hline(y=5.0, line_dash="dash", line_color="red", 
                  annotation_text="High Uncertainty Threshold",
                  annotation_position="right")
    
    fig.update_layout(
        title_text="L5-S1: Entropy vs Confidence (LSTV Detection Space)",
        xaxis_title="Peak Confidence",
        yaxis_title="Entropy",
        template='plotly_white',
        height=600,
        hovermode='closest'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id="scatter")


def create_level_comparison_plot(df: pd.DataFrame) -> str:
    """Create comparison plot across all levels"""
    
    levels = ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']
    level_labels = ['L1-L2', 'L2-L3', 'L3-L4', 'L4-L5', 'L5-S1']
    
    mean_entropy = [df[f'{level}_entropy'].mean() for level in levels]
    std_entropy = [df[f'{level}_entropy'].std() for level in levels]
    
    mean_conf = [df[f'{level}_confidence'].mean() for level in levels]
    std_conf = [df[f'{level}_confidence'].std() for level in levels]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Mean Entropy by Level', 'Mean Confidence by Level']
    )
    
    fig.add_trace(
        go.Bar(
            x=level_labels,
            y=mean_entropy,
            error_y=dict(type='data', array=std_entropy),
            marker_color='#9f7aea',
            name='Entropy'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=level_labels,
            y=mean_conf,
            error_y=dict(type='data', array=std_conf),
            marker_color='#48bb78',
            name='Confidence'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title_text="Mean Uncertainty Metrics by Vertebral Level",
        showlegend=False,
        height=500,
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Level")
    fig.update_yaxes(title_text="Entropy", row=1, col=1)
    fig.update_yaxes(title_text="Confidence", row=1, col=2)
    
    return fig.to_html(include_plotlyjs=False, div_id="level_comp")


def generate_report(csv_path: Path, output_path: Path, debug_dir: Path = None):
    """Generate HTML report from results CSV"""
    
    logger.info(f"Loading results from {csv_path}")
    df = pd.read_csv(csv_path)
    
    logger.info(f"Loaded {len(df)} studies")
    
    # Calculate statistics
    high_uncertainty = (df['l5_s1_entropy'] > 5.0).sum()
    detection_rate = (high_uncertainty / len(df) * 100) if len(df) > 0 else 0
    
    stats = {
        'total_studies': len(df),
        'high_uncertainty': high_uncertainty,
        'detection_rate': f"{detection_rate:.1f}",
        'mean_l5_s1_entropy': f"{df['l5_s1_entropy'].mean():.2f}"
    }
    
    # Create plots
    logger.info("Generating plots...")
    entropy_plot = create_entropy_distribution_plot(df)
    confidence_plot = create_confidence_distribution_plot(df)
    scatter_plot = create_scatter_plot(df)
    level_plot = create_level_comparison_plot(df)
    
    # Get top candidates
    df_sorted = df.sort_values('l5_s1_entropy', ascending=False).head(20)
    
    top_candidates = []
    for _, row in df_sorted.iterrows():
        entropy = row['l5_s1_entropy']
        
        if entropy > 5.5:
            risk_class = 'lstv-high'
            risk_label = 'HIGH'
        elif entropy > 4.0:
            risk_class = 'lstv-medium'
            risk_label = 'MEDIUM'
        else:
            risk_class = 'lstv-low'
            risk_label = 'LOW'
        
        top_candidates.append({
            'study_id': row['study_id'],
            'l5_s1_entropy': row['l5_s1_entropy'],
            'l5_s1_confidence': row['l5_s1_confidence'],
            'l4_l5_entropy': row['l4_l5_entropy'],
            'risk_class': risk_class,
            'risk_label': risk_label
        })
    
    # Load debug images if available
    debug_images = []
    if debug_dir and debug_dir.exists():
        logger.info(f"Loading debug images from {debug_dir}")
        for img_path in sorted(debug_dir.glob('*.png')):
            with open(img_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            debug_images.append({
                'title': img_path.stem.replace('_', ' ').title(),
                'base64': img_data
            })
        logger.info(f"Loaded {len(debug_images)} debug images")
    
    # Render template
    from datetime import datetime
    template = Template(HTML_TEMPLATE)
    html = template.render(
        stats=stats,
        entropy_distribution_plot=entropy_plot,
        confidence_distribution_plot=confidence_plot,
        scatter_plot=scatter_plot,
        level_comparison_plot=level_plot,
        top_candidates=top_candidates,
        debug_images=debug_images,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Save report
    logger.info(f"Saving report to {output_path}")
    output_path.write_text(html)
    logger.info("Report generated successfully!")


def main():
    parser = argparse.ArgumentParser(description='Generate LSTV Uncertainty Report')
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to lstv_uncertainty_metrics.csv')
    parser.add_argument('--output', type=str, required=True,
                       help='Output HTML file path')
    parser.add_argument('--debug_dir', type=str, default=None,
                       help='Directory containing debug visualizations')
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv)
    output_path = Path(args.output)
    debug_dir = Path(args.debug_dir) if args.debug_dir else None
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    generate_report(csv_path, output_path, debug_dir)


if __name__ == '__main__':
    main()
