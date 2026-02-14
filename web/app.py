#!/usr/bin/env python3
"""
Interactive LSTV Detection Web Demo
For tech fair demonstration
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import numpy as np
import pandas as pd
import pydicom
from pathlib import Path
import json
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tempfile

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Mock model for demo purposes
class MockLSTVDetector:
    """Mock detector for demo"""
    
    @staticmethod
    def calculate_uncertainty(image_data):
        """Calculate mock uncertainty from image data"""
        # Simulate different uncertainty levels
        mean_val = np.mean(image_data)
        std_val = np.std(image_data)
        
        # Generate plausible metrics
        entropies = {
            'l1_l2': np.random.uniform(2.0, 3.5),
            'l2_l3': np.random.uniform(2.2, 3.8),
            'l3_l4': np.random.uniform(2.5, 4.0),
            'l4_l5': np.random.uniform(3.0, 5.5),  # Higher uncertainty
            'l5_s1': np.random.uniform(4.0, 6.5),  # Highest uncertainty
        }
        
        confidences = {
            'l1_l2': np.random.uniform(0.75, 0.95),
            'l2_l3': np.random.uniform(0.70, 0.92),
            'l3_l4': np.random.uniform(0.65, 0.88),
            'l4_l5': np.random.uniform(0.40, 0.75),
            'l5_s1': np.random.uniform(0.30, 0.65),
        }
        
        # Determine LSTV risk
        l5_s1_entropy = entropies['l5_s1']
        if l5_s1_entropy > 5.5:
            risk = "HIGH"
            risk_color = "#e53e3e"
        elif l5_s1_entropy > 4.5:
            risk = "MEDIUM"
            risk_color = "#dd6b20"
        else:
            risk = "LOW"
            risk_color = "#38a169"
        
        return {
            'entropies': entropies,
            'confidences': confidences,
            'risk_level': risk,
            'risk_color': risk_color,
            'l5_s1_entropy': l5_s1_entropy
        }


detector = MockLSTVDetector()


@app.route('/')
def index():
    """Main demo page"""
    return render_template('demo.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze uploaded DICOM file"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save uploaded file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Read DICOM
        dcm = pydicom.dcmread(filepath)
        image_data = dcm.pixel_array
        
        # Normalize image for display
        img_min, img_max = image_data.min(), image_data.max()
        if img_max > img_min:
            image_normalized = ((image_data - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        else:
            image_normalized = np.zeros_like(image_data, dtype=np.uint8)
        
        # Convert to base64 for web display
        plt.figure(figsize=(6, 6))
        plt.imshow(image_normalized, cmap='gray')
        plt.axis('off')
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        # Calculate uncertainty
        results = detector.calculate_uncertainty(image_data)
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # Entropy plot
        levels = ['L1-L2', 'L2-L3', 'L3-L4', 'L4-L5', 'L5-S1']
        entropies = [results['entropies'][k] for k in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']]
        colors = ['#4299e1', '#48bb78', '#ed8936', '#f56565', '#9f7aea']
        
        bars1 = ax1.bar(levels, entropies, color=colors, alpha=0.7)
        ax1.axhline(y=5.0, color='red', linestyle='--', label='High Risk Threshold')
        ax1.set_ylabel('Entropy', fontsize=12, fontweight='bold')
        ax1.set_title('Uncertainty by Level', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Confidence plot
        confidences = [results['confidences'][k] for k in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']]
        bars2 = ax2.bar(levels, confidences, color=colors, alpha=0.7)
        ax2.set_ylabel('Peak Confidence', fontsize=12, fontweight='bold')
        ax2.set_title('Confidence by Level', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0, 1])
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        plot_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        # Clean up
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'image': image_base64,
            'plot': plot_base64,
            'entropies': results['entropies'],
            'confidences': results['confidences'],
            'risk_level': results['risk_level'],
            'risk_color': results['risk_color'],
            'l5_s1_entropy': results['l5_s1_entropy'],
            'patient_info': {
                'patient_id': str(dcm.PatientID) if hasattr(dcm, 'PatientID') else 'Unknown',
                'study_date': str(dcm.StudyDate) if hasattr(dcm, 'StudyDate') else 'Unknown',
                'modality': str(dcm.Modality) if hasattr(dcm, 'Modality') else 'Unknown',
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/demo_data')
def demo_data():
    """Get demo statistics"""
    
    # Generate demo statistics
    stats = {
        'total_analyzed': np.random.randint(450, 550),
        'high_risk': np.random.randint(30, 50),
        'medium_risk': np.random.randint(60, 90),
        'low_risk': np.random.randint(350, 420),
        'detection_rate': round(np.random.uniform(8, 12), 1)
    }
    
    return jsonify(stats)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
