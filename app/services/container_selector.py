# -*- coding: utf-8 -*-
"""
Servicio de Selección Inteligente de Contenedores KPU
Analiza el código y selecciona automáticamente el contenedor Docker óptimo
"""

import re
from typing import Dict, List, Tuple

class ContainerSelector:
    """
    Selecciona automáticamente el contenedor Docker óptimo basándose en:
    - Librerías importadas en el código
    - Palabras clave en comentarios
    - Operaciones detectadas
    """
    
    # Mapeo de imports a contenedores
    LIBRARY_TO_CONTAINER = {
        # NLP
        'transformers': 'py-nlp',
        'spacy': 'py-nlp',
        'nltk': 'py-nlp',
        'gensim': 'py-nlp',
        'textblob': 'py-nlp',
        'langdetect': 'py-nlp',
        'wordcloud': 'py-nlp',
        
        # OCR y Documentos
        'pytesseract': 'py-ocr',
        'pdf2image': 'py-ocr',
        'PyPDF2': 'py-ocr',
        'pdfplumber': 'py-ocr',
        'easyocr': 'py-ocr',
        'docx2txt': 'py-ocr',
        'openpyxl': 'py-ocr',
        'tabula': 'py-ocr',
        
        # Geoespacial
        'geopandas': 'py-geo',
        'folium': 'py-geo',
        'geopy': 'py-geo',
        'shapely': 'py-geo',
        'osmnx': 'py-geo',
        
        # Series Temporales
        'prophet': 'py-timeseries',
        'pmdarima': 'py-timeseries',
        'statsmodels': 'py-timeseries',
        'arch': 'py-timeseries',
        'tslearn': 'py-timeseries',
        'tsfresh': 'py-timeseries',
        
        # Web Scraping
        'selenium': 'py-web',
        'playwright': 'py-web',
        'scrapy': 'py-web',
        'beautifulsoup4': 'py-web',
        'bs4': 'py-web',
        'requests_html': 'py-web',
        'trafilatura': 'py-web',
        
        # Procesamiento de Imágenes Avanzado
        'face_recognition': 'py-image',
        'rembg': 'py-image',
        'mediapipe': 'py-image',
        'qrcode': 'py-image',
        'pyzbar': 'py-image',
        'albumentations': 'py-image',
        
        # Crypto y Finanzas
        'ccxt': 'py-crypto',
        'yfinance': 'py-crypto',
        'pandas_ta': 'py-crypto',
        'web3': 'py-crypto',
        'binance': 'py-crypto',
        'backtrader': 'py-crypto',
        
        # Bioinformática
        'biopython': 'py-bio',
        'Bio': 'py-bio',
        'ete3': 'py-bio',
        'pysam': 'py-bio',
        
        # Redes y Seguridad
        'scapy': 'py-network',
        'nmap': 'py-network',
        'impacket': 'py-network',
        'paramiko': 'py-network',
        'fabric': 'py-network',
        
        # 3D
        'trimesh': 'py-3d',
        'pyvista': 'py-3d',
        'open3d': 'py-3d',
        'meshio': 'py-3d',
        
        # Música
        'librosa': 'py-music',
        'music21': 'py-music',
        'pretty_midi': 'py-music',
        'mido': 'py-music',
        
        # Audio/Video
        'moviepy': 'py-audio',
        'pydub': 'py-audio',
        
        # Gráficos
        'matplotlib': 'py-graph',
        'seaborn': 'py-graph',
        'plotly': 'py-graph',
        'bokeh': 'py-graph',
        'networkx': 'py-graph',
        'graphviz': 'py-graph',
    }
    
    # Palabras clave en comentarios/código que sugieren un contenedor
    KEYWORD_TO_CONTAINER = {
        'py-nlp': ['nlp', 'sentiment', 'tokeniz', 'embed', 'translate', 'ner', 'pos tag', 'language'],
        'py-ocr': ['ocr', 'tesseract', 'pdf', 'document', 'scan', 'excel', 'word'],
        'py-geo': ['geo', 'map', 'location', 'gps', 'coordinate', 'latitude', 'longitude'],
        'py-timeseries': ['forecast', 'predict', 'time series', 'arima', 'seasonal', 'trend'],
        'py-web': ['scrape', 'crawl', 'selenium', 'browser', 'web', 'html'],
        'py-image': ['face', 'qr', 'background', 'detection', 'pose'],
        'py-crypto': ['crypto', 'bitcoin', 'ethereum', 'trading', 'exchange', 'blockchain'],
        'py-bio': ['dna', 'rna', 'genome', 'sequence', 'protein', 'bioinformatic'],
        'py-network': ['network', 'port', 'scan', 'packet', 'ssh', 'security'],
        'py-3d': ['3d', 'mesh', 'stl', 'obj', 'geometry', 'model'],
        'py-music': ['music', 'audio', 'tempo', 'midi', 'beat', 'chord'],
        'py-audio': ['video', 'audio', 'extract', 'convert', 'ffmpeg'],
        'py-graph': ['plot', 'chart', 'graph', 'visual', 'diagram'],
    }
    
    @staticmethod
    def extract_imports(code: str) -> List[str]:
        """Extrae todas las librerías importadas del código"""
        imports = []
        
        # Patrones: import xxx, from xxx import yyy
        import_patterns = [
            r'^\s*import\s+([\w\.]+)',
            r'^\s*from\s+([\w\.]+)\s+import',
        ]
        
        for line in code.split('\n'):
            for pattern in import_patterns:
                match = re.search(pattern, line)
                if match:
                    lib = match.group(1).split('.')[0]  # Primera parte del import
                    imports.append(lib)
        
        return imports
    
    @staticmethod
    def extract_keywords(code: str) -> List[str]:
        """Extrae palabras clave relevantes de comentarios y strings"""
        keywords = []
        
        # Extraer comentarios
        comment_pattern = r'#\s*(.+)$'
        for line in code.split('\n'):
            match = re.search(comment_pattern, line)
            if match:
                keywords.extend(match.group(1).lower().split())
        
        # Extraer strings entre comillas
        string_pattern = r'["\']([^"\']+)["\']'
        for match in re.finditer(string_pattern, code):
            keywords.extend(match.group(1).lower().split())
        
        return keywords
    
    @classmethod
    def select_container(cls, code: str) -> Tuple[str, Dict[str, int]]:
        """
        Selecciona el contenedor óptimo para ejecutar el código
        
        Returns:
            Tuple[str, Dict[str, int]]: (nombre_contenedor, scores_por_contenedor)
        """
        scores = {}
        
        # Analizar imports
        imports = cls.extract_imports(code)
        for imp in imports:
            if imp in cls.LIBRARY_TO_CONTAINER:
                container = cls.LIBRARY_TO_CONTAINER[imp]
                scores[container] = scores.get(container, 0) + 10  # Peso alto para imports
        
        # Analizar keywords
        keywords = cls.extract_keywords(code)
        for container, kws in cls.KEYWORD_TO_CONTAINER.items():
            for kw in kws:
                if any(kw in keyword for keyword in keywords):
                    scores[container] = scores.get(container, 0) + 1
        
        # Si no hay coincidencias claras, usar py-graph como default
        if not scores:
            return 'py-graph', {'py-graph': 0}
        
        # Retornar el contenedor con mayor score
        best_container = max(scores.items(), key=lambda x: x[1])[0]
        return best_container, scores
    
    @classmethod
    def suggest_containers(cls, task_description: str) -> List[Tuple[str, int]]:
        """
        Sugiere contenedores basándose en descripción de tarea en lenguaje natural
        
        Returns:
            Lista de (contenedor, score) ordenada por relevancia
        """
        scores = {}
        task_lower = task_description.lower()
        
        for container, keywords in cls.KEYWORD_TO_CONTAINER.items():
            score = 0
            for keyword in keywords:
                if keyword in task_lower:
                    score += 1
            if score > 0:
                scores[container] = score
        
        # Ordenar por score descendente
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# Ejemplos de uso
if __name__ == "__main__":
    # Ejemplo 1: Análisis de sentimientos
    code1 = """
    # Análisis de sentimiento en redes sociales
    from transformers import pipeline
    import pandas as pd
    
    sentiment_analyzer = pipeline('sentiment-analysis')
    result = sentiment_analyzer("I love this product!")
    """
    
    container, scores = ContainerSelector.select_container(code1)
    print(f"Código 1 -> Contenedor: {container}, Scores: {scores}")
    
    # Ejemplo 2: Scraping web
    code2 = """
    # Scraping de noticias
    from selenium import webdriver
    from bs4 import BeautifulSoup
    
    driver = webdriver.Chrome()
    driver.get('https://news.ycombinator.com')
    """
    
    container, scores = ContainerSelector.select_container(code2)
    print(f"Código 2 -> Contenedor: {container}, Scores: {scores}")
    
    # Ejemplo 3: Descripción de tarea
    suggestions = ContainerSelector.suggest_containers(
        "Necesito extraer texto de un PDF escaneado y hacer OCR"
    )
    print(f"Sugerencias para OCR: {suggestions}")
