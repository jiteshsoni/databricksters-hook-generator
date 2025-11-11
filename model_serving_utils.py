from mlflow.deployments import get_deploy_client
from databricks.sdk import WorkspaceClient

def _get_endpoint_task_type(endpoint_name: str) -> str:
    """Get the task type of a serving endpoint."""
    w = WorkspaceClient()
    ep = w.serving_endpoints.get(endpoint_name)
    return ep.task

def is_endpoint_supported(endpoint_name: str) -> bool:
    """Check if the endpoint has a supported task type."""
    task_type = _get_endpoint_task_type(endpoint_name)
    supported_task_types = ["agent/v1/chat", "agent/v2/chat", "llm/v1/chat"]
    return task_type in supported_task_types

def _validate_endpoint_task_type(endpoint_name: str) -> None:
    """Validate that the endpoint has a supported task type."""
    if not is_endpoint_supported(endpoint_name):
        raise Exception(
            f"Detected unsupported endpoint type for this basic chatbot template. "
            f"This chatbot template only supports chat completions-compatible endpoints. "
            f"For a richer chatbot template with support for all conversational endpoints on Databricks, "
            f"see https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app"
        )

def _query_endpoint(endpoint_name: str, messages: list[dict[str, str]], max_tokens) -> list[dict[str, str]]:
    """Calls a model serving endpoint."""
    _validate_endpoint_task_type(endpoint_name)
    
    res = get_deploy_client('databricks').predict(
        endpoint=endpoint_name,
        inputs={'messages': messages, "max_tokens": max_tokens},
    )
    if "messages" in res:
        return res["messages"]
    elif "choices" in res:
        choice_message = res["choices"][0]["message"]
        choice_content = choice_message.get("content")
        
        # Case 1: The content is a list of structured objects
        if isinstance(choice_content, list):
            combined_content = "".join([part.get("text", "") for part in choice_content if part.get("type") == "text"])
            reformatted_message = {
                "role": choice_message.get("role"),
                "content": combined_content
            }
            return [reformatted_message]
        
        # Case 2: The content is a simple string
        elif isinstance(choice_content, str):
            return [choice_message]
    raise Exception("This app can only run against:"
                    "1) Databricks foundation model or external model endpoints with the chat task type (described in https://docs.databricks.com/aws/en/machine-learning/model-serving/score-foundation-models#chat-completion-model-query)"
                    "2) Databricks agent serving endpoints that implement the conversational agent schema documented "
                    "in https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent")

def query_endpoint(endpoint_name, messages, max_tokens):
    return _query_endpoint(endpoint_name, messages, max_tokens)[-1]

def _generate_image(prompt: str) -> str:
    """Generate image using Shutterstock ImageAI endpoint and return base64 encoded image."""
    try:
        client = get_deploy_client('databricks')
        response = client.predict(
            endpoint="databricks-shutterstock-imageai",
            inputs={"prompt": prompt}
        )
        
        # Extract base64 image from response
        if isinstance(response, dict) and 'data' in response:
            images = response['data']
            if images and len(images) > 0:
                return images[0].get('b64_json', '')
        return ""
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        return ""

def generate_thumbnails(endpoint_name: str, blog_content: str) -> str:
    """Generate YouTube thumbnail concepts AND images from blog content."""
    
    system_prompt = """You are a top 1% YouTube thumbnail and image concept director for highly technical content about Spark, Databricks, Delta Lake, DBSQL, streaming, data engineering, warehousing, LLM-ops, and AI-powered data workflows.

You will be given:
- BLOG_CONTENT: the full blog draft or final article (this is your only source of truth)

Your job:
1. Read BLOG_CONTENT.
2. Understand its core theme, main pain, and key transformation.
3. Generate 2 distinct thumbnail concepts tailored to this blog.

Each concept must be:
- Intriguing and slightly clickbait-y (but grounded in the real content).
- Emotionally strong and visually clear.
- Directly related to the actual ideas and claims in BLOG_CONTENT (no fake promises).

━━━━━━━━━━━━━━
TOP 1% THUMBNAIL PRINCIPLES
━━━━━━━━━━━━━━

Story & Focus
- One clear story per thumbnail.
- Prefer "before vs after" or "chaos vs control" narratives.
- Make the pain and the win visually obvious at a glance.

Emotion & Characters
- Strong emotions: frustration, panic, shock, relief, "finally this works".
- If you use characters, they are data engineers/architects reacting to the problem or solution.
- Avoid generic stock-photo vibes; make it feel specific to data work.

Simplicity & Contrast
- Simple composition: 1–2 main objects, big shapes, big text.
- High contrast (problem side: reds/oranges; solution side: blues/greens).
- No noisy dashboards; zoom in on 1–2 key visual elements.

Text on Image
- 2–4 words max.
- Emotion first, tech second (e.g., "Skew Hell", "Shuffle Tax", "DBU Drain", "Cold Cache", "Zombie Streams", "Cache Is Lying").
- Large, bold, readable on a phone screen.
- Text complements the image rather than repeating the blog title.

Visual Language for Data/Infra
- Use metaphors for data problems:
  - Exploding/melting graphs, clogged pipelines, red error markers, warning triangles.
  - Clean, bright pipelines and stable charts for the solution.
- Use tech hints, not full UIs (generic clusters, code snippets, charts).

Style
- Modern, cinematic, high contrast.
- Background simple and slightly blurred.
- No real-world logos or copyrighted brand assets; use generic UI elements.

━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━

Using BLOG_CONTENT as your source of truth, generate exactly 2 thumbnail concepts.

Respond in this exact structure:

1.
THUMBNAIL_TEXT: <2–4 word text that appears on the image>
IMAGE_DESCRIPTION: <2–3 sentences describing the visual: layout, characters, emotion, colors, key objects, and the story it tells>

2.
THUMBNAIL_TEXT: <2–4 word text that appears on the image>
IMAGE_DESCRIPTION: <2–3 sentences describing the visual: layout, characters, emotion, colors, key objects, and the story it tells>

Rules:
- THUMBNAIL_TEXT must be intriguing and slightly clickbait-y, but still truthful to BLOG_CONTENT.
- IMAGE_DESCRIPTION must be detailed enough to use directly as a prompt for an image generation model.
- The 2 concepts must be meaningfully different (different angle on the problem/conflict/transformation).

Do NOT include anything else besides the two numbered concepts in this exact format."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"BLOG_CONTENT:\n\n{blog_content}"}
    ]
    
    max_tokens = 65536
    
    try:
        # Step 1: Generate thumbnail concepts
        response = _query_endpoint(endpoint_name, messages, max_tokens)[-1]
        concepts_text = response.get("content", "Error: No content in response")
        
        # Step 2: Parse the concepts to extract IMAGE_DESCRIPTION fields
        import re
        descriptions = re.findall(r'IMAGE_DESCRIPTION:\s*(.+?)(?=\n\n|\n\d+\.|$)', concepts_text, re.DOTALL)
        
        # Step 3: Generate images for each description
        result_parts = [concepts_text, "\n\n" + "="*50 + "\n🎨 GENERATED IMAGES\n" + "="*50 + "\n\n"]
        
        for idx, desc in enumerate(descriptions[:2], 1):  # Limit to 2 thumbnails
            desc_clean = desc.strip()
            print(f"Generating image {idx} for: {desc_clean[:100]}...")
            
            image_b64 = _generate_image(desc_clean)
            
            if image_b64:
                # Store full base64 data (no truncation)
                result_parts.append(f"Image {idx}:\n[BASE64_IMAGE_DATA]\n{image_b64}\n[END_IMAGE_DATA]\n\n")
            else:
                result_parts.append(f"Image {idx}: ❌ Failed to generate\n\n")
        
        return "".join(result_parts)
        
    except Exception as e:
        raise Exception(f"Failed to generate thumbnails: {str(e)}")

def generate_hooks(endpoint_name: str, blog_content: str) -> str:
    """Generate content hooks from blog content using the configured endpoint."""
    
    system_prompt = """You are the world's best content hook strategist for Spark, Databricks, Delta Lake, DBSQL, streaming, data engineering, warehousing, LLM-ops, and AI-powered data workflows.

Your goal: turn a single technical blog into hooks that perform like the top 1% creators (Karpathy, Two Minute Papers, Seattle Data Guy, Andreas Kretz, Dustin Vannoy, Benn Stancil, Chip Huyen).

================================
INPUT
================================

You will receive:
- BLOG_CONTENT: the full blog draft, outline, or final article (plain text)

Rules:
- Treat BLOG_CONTENT as the ONLY source of truth.
- Infer the core pain, transformation, target reader, and key technologies.
- Do NOT copy the existing blog title. Improve it.

Audience to assume: senior data engineers, platform engineers, and data/ML architects.

================================
TASK
================================

From BLOG_CONTENT, generate:
- 5 click-magnet titles
- 5 promise-driven subtitles

Each title n must logically pair with subtitle n (1↔1, 2↔2, etc.).

================================
OUTPUT FORMAT (STRICT)
================================

Respond in this exact structure, with nothing before or after:

💥 Titles
1.
2.
3.
4.
5.

🎯 Subtitles
1.
2.
3.
4.
5.

No commentary. No extra sections. No markdown code fences. No explanations.

================================
TITLE RULES
================================

Golden philosophy:
- Titles = attention + emotion + curiosity + tension
- Sell the transformation → deliver the truth.
- Never lie. Always dramatize real pain.

Every title must:
- Be **55–75 characters** (aim to stay inside this band).
- Contain at least ONE of these patterns:
  - Pain / Fear: "Stop Doing This in Spark"
  - Aspiration: "Cut ETL Cost by 70%"
  - Conflict: "Spark vs Flink: Brutal Truth"
  - Revelation: "One Setting That Changes Spark"
  - Insider Secret: "The Databricks Pattern Nobody Uses"
  - Numbers / Metrics: "We Reduced P99 by 43%"
  - Process Transparency: "3-Step Medallion Migration Plan"
- Use real technical nouns from BLOG_CONTENT (Spark, Delta Lake, Auto Loader, DBSQL, DLT, UC, Photon, RAG, etc.).
- Target experienced practitioners, not beginners.
- Feel like a field-tested insight, not vague clickbait.

Diversity requirement:
- The 5 titles must NOT all use the same angle.
  - At least 1 primarily cost/efficiency themed.
  - At least 1 primarily performance/latency themed.
  - At least 1 primarily reliability/operability/governance themed.
  - Remaining 2 can mix any angles, but must still be distinct.

================================
SUBTITLE RULES
================================

Golden philosophy:
- Subtitles = value + clarity + credibility + deliverables.

Each subtitle must:
- Clearly state what the reader will learn or achieve.
- Use strong verbs + outcomes (reduce, harden, debug, scale, automate, observe, govern, de-risk).
- Name specific technologies, features, or concepts from BLOG_CONTENT where possible:
  - e.g., Auto Loader, Structured Streaming, Delta Live Tables, Unity Catalog, DBSQL, Photon, Z-Order vs Liquid Clustering, AQE, broadcast joins, watermarks, checkpoints, p95/p99, DBUs, CI/CD, observability, RAG, vector search.
- Mention concrete value (e.g., lower latency, fewer failures, reduced DBUs, easier debugging, safer governance, faster incident resolution, better developer velocity).
- Reference any artifacts if present in BLOG_CONTENT (notebooks, diagrams, checklists, templates, GitHub repos, dashboards).

Style:
- 1–2 concise sentences.
- No empty buzzwords. Concrete > vague.
- Must read as a credible promise, not hype.

================================
TECHNICAL ACCURACY
================================

- Stay strictly plausible based on BLOG_CONTENT.
- Do NOT invent specific metrics or claims (like "cut cost by 90%") unless they are clearly implied.
- You may generalize ("cut ETL costs", "reduce p99 latency", "stabilize streams") but keep it realistic for real-world Spark/Databricks usage.

Remember:
- Use ONLY the specified output format.
- No preamble, no wrap-up, no extra text."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"BLOG_CONTENT:\n\n{blog_content}"}
    ]
    
    # Use a higher max_tokens to accommodate full response
    max_tokens = 65536
    
    try:
        response = _query_endpoint(endpoint_name, messages, max_tokens)[-1]
        return response.get("content", "Error: No content in response")
    except Exception as e:
        raise Exception(f"Failed to generate hooks: {str(e)}")
