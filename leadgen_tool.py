import streamlit as st
import pandas as pd
import tempfile
import os
from llama_cpp import Llama
from serpapi import GoogleSearch


LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH")
llm = Llama(model_path=LLAMA_MODEL_PATH, n_ctx=2048)


def ask_model(prompt):
    response = llm(prompt, max_tokens=768, temperature=0.7, top_p=0.95, stop=["</s>"])
    return response['choices'][0]['text'].strip()


def get_critic_feedback(draft):
    feedback_prompt = f"""
You are an expert sales communication coach.
Review the following outreach email and provide a brief critique along with actionable suggestions for improving tone, personalization, and clarity:

---
{draft}
---

List specific improvements. 
If the email is excellent and viable, only then say 'APPROVED' or else dont add this word.
"""
    return ask_model(feedback_prompt)


SERP_API_KEY = os.getenv("SERPAPI_API_KEY")

def browse_person_info(name):
    if GoogleSearch is None:
        return "(Unable to fetch insights - SerpAPI not available)"
    try:
        search = GoogleSearch({
            "q": f"{name} favorite vacation destinations USA",
            "api_key": SERP_API_KEY
        })
        results = search.get_dict()
        snippets = []
        for res in results.get("organic_results", [])[:5]:
            title = res.get("title", "")
            snippet = res.get("snippet", "")
            snippets.append(f"{title}: {snippet}")
        return "\n".join(snippets)
    except Exception as e:
        return f"(Error fetching search results: {e})"


def get_email_prompt(name, insights, feedback=""):
    return f"""
You are a senior travel advisor at Inspirato, a luxury travel company offering personalized and premium vacation experiences.

Write a friendly, connective, and professional sales outreach email to {name}.
Base the email on the vacation-related insight and any feedback provided below.
Clearly highlight the unique offerings of Inspirato as seen on https://www.inspirato.com, including:
- Dozens of luxury vacation destinations in the U.S. and worldwide
- Curated residences, five-star hotels, and adventure experiences
- Premium services such as dedicated concierge planning, members-only rates, and flexible travel options

Vacation-related insight:
{insights}

Previous feedback or improvement notes:
{feedback}

The email should:
- Open with a warm greeting
- Make an effort to genuinely connect with {name}
- Use the insight to establish common ground or interest
- Emphasize the value of Inspirato’s service
- End with an engaging and clear call to action

Keep the tone conversational, sincere, and polished.
Write the entire email below:-
-----------------------------------------------------
"""


def process_lead(row):
    try:
        name = row['name']
        insights = browse_person_info(name)
        draft_prompt = get_email_prompt(name, insights)
        draft = ask_model(draft_prompt)
        feedback = get_critic_feedback(draft)
        if "APPROVED" not in feedback.upper():
            refined_prompt = get_email_prompt(name, insights, feedback)
            draft = ask_model(refined_prompt)
        print(f"Draft for {name}:\n{draft}\nFeedback: {feedback}")
        return draft.strip()
    except Exception as e:
        return f"(Failed to generate email for {row.get('name', 'Unknown')}: {e})"


st.title("📧 Lead Gen Email Writer (LLaMA 2 7B Quantized + SerpAPI)")
st.markdown("Upload a CSV with `name` column. The app will generate outreach emails and return a downloadable file.")

uploaded_file = st.file_uploader("Choose your leads CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if 'name' in df.columns:
        with st.spinner("Generating emails with LLaMA 2 and SerpAPI..."):
            try:
                results = [process_lead(row) for _, row in df.iterrows()]
            except Exception as e:
                st.error(f"🚨 Processing error: {e}")
                results = []

        if results:
            df['email_text'] = results

            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                df.to_csv(tmp.name, index=False)
                st.success("✅ Emails generated successfully!")
                st.download_button(
                label="📥 Download Updated CSV",
                data=open(tmp.name, 'rb'),
                file_name="leads_with_emails.csv",
                mime="text/csv"
            )
            st.info("📂 You can now upload a new CSV to generate more emails.")
    else:
        st.error("❌ The uploaded file must contain a 'name' column.")