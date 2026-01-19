import os
import json
import requests
import urllib.parse
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

# Credentials
API_KEY = os.getenv("POLLINATIONS_API_KEY", "pk_nnWqebk9TtNY5Md8")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase (optional, only if credentials provided)
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_ideas(text):
    """
    Uses Pollinations.ai text API to split text into distinct visual prompts.
    Uses the API key for higher limits and stability.
    """
    system_prompt = "Extract the distinct visual ideas from the following sentences and rewrite each as a short, vivid prompt for an image generator (DALL-E style). Return ONLY a JSON list of strings. No other text."
    user_content = f"{system_prompt}\n\nInput text: {text}"
    
    encoded_text = urllib.parse.quote(user_content)
    # Adding key= parameter to the text API
    url = f"https://text.pollinations.ai/{encoded_text}?key={API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text.strip()
            # Clean up potential markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            prompts = json.loads(content)
            if isinstance(prompts, list):
                return prompts
            elif isinstance(prompts, dict):
                for val in prompts.values():
                    if isinstance(val, list):
                        return val
        return [text]
    except Exception as e:
        print(f"Extraction Error: {e}")
        return [s.strip() for s in text.split('.') if len(s.strip()) > 5]

@app.route('/')
def index():
    return render_template('index.html')

from flask import Flask, render_template, request, jsonify, Response, stream_with_context

@app.route('/image_proxy')
def image_proxy():
    prompt = request.args.get('prompt', '')
    seed = request.args.get('seed', '')
    width = request.args.get('width', '768')
    height = request.args.get('height', '768')
    nologo = request.args.get('nologo', 'true')
    
    if not prompt:
        return "No prompt provided", 400

    encoded_prompt = urllib.parse.quote(prompt)
    target_url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo={nologo}&model=flux"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        req = requests.get(target_url, headers=headers, stream=True)
        # Exclude headers that should be handled by the local Flask server
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in req.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(stream_with_context(req.iter_content(chunk_size=1024)), 
                        status=req.status_code, 
                        headers=headers)
    except Exception as e:
        return str(e), 500

import random

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        # Step 1: Extract distinct ideas
        prompts = extract_ideas(text)
        
        if not prompts:
            return jsonify({'error': 'Could not extract ideas from text'}), 400

        # Step 2: Construct image URLs using our local proxy
        results = []
        for prompt in prompts:
            # Use random integer for seed as required by API
            seed = random.randint(0, 1000000000)
            
            # Use our internal proxy to handle Auth headers
            image_url = (
                f"/image_proxy?prompt={urllib.parse.quote(prompt)}"
                f"&width=768&height=768&seed={seed}&nologo=true"
            )
            
            results.append({
                'prompt': prompt,
                'url': image_url
            })
            
            # Log to Supabase if configured
            if supabase:
                try:
                    supabase.table("generations").insert({
                        "prompt": prompt,
                        "image_url": image_url,
                        "seed": str(seed)
                    }).execute()
                except Exception as e:
                    print(f"Supabase Logging Error: {e}")

        return jsonify({'images': results})

    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting app on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
