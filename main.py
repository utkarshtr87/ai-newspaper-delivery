import os
import json
import google.generativeai as genai
import feedparser
from weasyprint import HTML, CSS
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY secret not found!")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

ENGLISH_RSS_FEEDS = [
    "https://www.thehindu.com/feeder/default.rss",
    "https://indianexpress.com/feed/",
    "https://www.indiatoday.in/rss/1206584"
]
HINDI_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/hindi/rss.xml",
    "https://www.jagran.com/rss/news/latest.xml",
    "https://www.livehindustan.com/rss/latest-news.xml"
]

SMART_PROMPT = """
You are a neutral, senior news analyst for "Unmasked India". Analyze the following article content.
1. Provide a factual, unbiased summary of the key events in about 150-200 words.
2. Explain the background of this issue in 2-3 simple points.
3. Present the main arguments from both sides (Pro and Con), if applicable.
4. Conclude with one open-ended, thought-provoking question (Manthan Point).
The final output must be in clear, accessible {language}.
The summary should be in HTML paragraph tags <p>, and the Manthan Point in a paragraph with class 'manthan-point'.

Article Title: {title}
Article Summary from RSS: {summary}
"""

# --- 2. CORE FUNCTIONS ---
def get_fresh_news(rss_urls, max_articles=20):
    print(f"Fetching fresh news...")
    articles = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:7]: # Get top 7 from each source
                articles.append({'title': entry.title, 'summary': entry.summary, 'link': entry.link})
        except Exception as e:
            print(f"  > Could not parse feed {url}: {e}")
    print(f"Fetched {len(articles)} total articles.")
    return articles[:max_articles]

def get_ai_analysis(articles, language):
    print(f"Starting AI analysis for {language} news...")
    analyzed_content = []
    for article in articles:
        try:
            prompt = SMART_PROMPT.format(language=language, title=article['title'], summary=article['summary'])
            response = model.generate_content(prompt)
            # Add the original title and the AI's response
            full_analysis = f"<h3>{article['title']}</h3>\n{response.text}"
            analyzed_content.append(full_analysis)
            print(f"  > Analyzed: {article['title']}")
        except Exception as e:
            print(f"  > AI analysis failed for '{article['title']}': {e}")
    return analyzed_content
    
def load_sponsors():
    """Loads sponsor data from the JSON file for both tiers."""
    try:
        with open('sponsors.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Smart check: if sponsors list is empty, don't show the section titles
            if not data.get("gold_sponsors", []):
                data["gold_sponsors"] = None
            if not data.get("silver_sponsors", []):
                data["silver_sponsors"] = None
            return data.get("gold_sponsors"), data.get("silver_sponsors")
    except FileNotFoundError:
        return None, None # Return None if no sponsor file

def generate_newspaper_html(analyzed_articles, gold_sponsors, silver_sponsors, language):
    """Fills the HTML template with sponsors and AI-generated content."""
    print("Generating HTML content with tiered sponsors...")
    with open('template.html', 'r', encoding='utf-8') as f:
        template_str = f.read()

    # Create HTML for GOLD sponsors
    gold_sponsors_html = ""
    if gold_sponsors:
        for sponsor in gold_sponsors:
            gold_sponsors_html += f'<img src="{sponsor["logo_url"]}" alt="{sponsor["name"]}">'
    else:
        # If no gold sponsors, hide the entire top section
        template_str = template_str.replace('<div class="sponsors-top">', '<div class="sponsors-top" style="display:none;">')

    # Create HTML for SILVER sponsors
    silver_sponsors_html = ""
    if silver_sponsors:
        for sponsor in silver_sponsors:
            silver_sponsors_html += f'<img src="{sponsor["logo_url"]}" alt="{sponsor["name"]}">'
    else:
        # If no silver sponsors, hide the entire bottom section
        template_str = template_str.replace('<div class="sponsors-bottom">', '<div class="sponsors-bottom" style="display:none;">')


    # Create HTML for articles
    articles_html_str = "".join([f"<article>{content}</article>" for content in analyzed_articles])
    
    ist = pytz.timezone('Asia/Kolkata')
    today_date_str = datetime.now(ist).strftime('%A, %d %B %Y')

    # Replace all placeholders
    final_html = template_str.replace('{{ gold_sponsors_html }}', gold_sponsors_html)
    final_html = final_html.replace('{{ silver_sponsors_html }}', silver_sponsors_html)
    final_html = final_html.replace('{{ today_date }}', today_date_str)
    final_html = final_html.replace('{{ articles_html }}', articles_html_str)
    
    if language == "Hindi":
        final_html = final_html.replace('<body>', '<body class="lang-hi">')

    return final_html

def convert_html_to_pdf(html_content, output_filename):
    print(f"Converting HTML to PDF: {output_filename}...")
    css_string = ""
    with open('style.css', 'r', encoding='utf-8') as f:
        css_string = f.read()
    
    css = CSS(string=css_string)
    HTML(string=html_content).write_pdf(output_filename, stylesheets=[css])
    print(f"PDF generation complete for {output_filename}!")


# --- 3. MAIN WORKFLOW ---
if __name__ == "__main__":
    gold_sponsors, silver_sponsors = load_sponsors()

    # --- English Newspaper ---
    print("--- Starting English Newspaper Generation (Unmasked India) ---")
    english_articles = get_fresh_news(ENGLISH_RSS_FEEDS)
    if english_articles:
        analyzed_english_articles = get_ai_analysis(english_articles, "English")
        final_english_html = generate_newspaper_html(analyzed_english_articles, gold_sponsors, silver_sponsors, "English")
        convert_html_to_pdf(final_english_html, "Unmasked_India_EN.pdf")

    print("\n" + "="*50 + "\n")

    # --- Hindi Newspaper ---
    print("--- Starting Hindi Newspaper Generation (Unmasked India) ---")
    hindi_articles = get_fresh_news(HINDI_RSS_FEEDS)
    if hindi_articles:
        analyzed_hindi_articles = get_ai_analysis(hindi_articles, "Hindi")
        final_hindi_html = generate_newspaper_html(analyzed_hindi_articles, gold_sponsors, silver_sponsors, "Hindi")
        convert_html_to_pdf(final_hindi_html, "Unmasked_India_HI.pdf")