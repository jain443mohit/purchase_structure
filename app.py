import streamlit as st
import pandas as pd
from graphviz import Digraph

# Set wide page configuration layout matching requirements
st.set_page_config(page_title="Model Output Rule Flowchart", layout="wide")

# --- SMART TEXT WRAPPER FOR NARROW VERTICAL NODES ---
def wrap_node_text(text):
    """
    Splits long comma-separated strings onto separate lines using newlines (\n).
    This keeps the Graphviz boxes narrow and forces a clean vertical tree structure.
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = text.strip()
    if "," in text:
        # Split by comma, clean spaces, and stack them vertically
        parts = [p.strip() for p in text.split(",")]
        return ",\n".join(parts)
    return text

# --- CELL VALUE PARSER ---
def extract_value_only(text):
    """
    Extracts only the value side of a 'key : value' string cell, discarding the key.
    """
    if pd.isna(text) or not isinstance(text, str):
        return None
    
    text = text.strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        text = text[1:-1].strip()
        
    if ":" in text:
        parts = text.split(":", 1)
        k = parts[0].strip().strip("'").strip('"')
        v = parts[1].strip().strip("'").strip('"')
        
        if not k and not v:
            return None
        return v if v else None
        
    return text if text else None

# --- GRAPHVIZ CONSTRUCTOR FOR BUSINESS USERS ---
def generate_business_flowchart(df_subset, level_cols, root_bu_name):
    """
    Creates a clean, strictly vertical decision tree flowchart.
    All paths originate from a single Business Unit root node at the top.
    Deduplicates edges and nodes to ensure arrows are never repeated.
    """
    # 'TB' sets the ranking direction from Top to Bottom (Vertical Format)
    # 'splines': 'true' ensures smooth arrow paths
    dot = Digraph(comment='Model Decision Path', graph_attr={'rankdir': 'TB', 'splines': 'true'})
    
    # Configure global graph layout design for a clean corporate presentation
    dot.attr('node', shape='box', style='filled,rounded', color='#1E3A8A', 
             fillcolor='#EFF6FF', fontname='Arial', fontsize='11', fontcolor='#1E3A8A')
    dot.attr('edge', color='#9CA3AF', penwidth='1.5', arrowhead='normal')

    # Create the single supreme root node at the top based on selected Business Unit
    root_id = "root_bu"
    dot.node(root_id, label=f"🏢 Business Unit:\n{root_bu_name}", fillcolor='#FEF3C7', color='#D97706', fontcolor='#92400E')

    # Dictionaries to guarantee we map absolute unique keys and never repeat an edge/arrow
    seen_nodes = {}
    seen_edges = set()
    
    def get_node_id(path_tuple):
        if path_tuple not in seen_nodes:
            seen_nodes[path_tuple] = f"node_{len(seen_nodes)}"
        return seen_nodes[path_tuple]

    # Process dataset line by line to piece the tree structure together
    for _, row in df_subset.iterrows():
        current_path = []
        
        for col in level_cols:
            val = extract_value_only(row[col])
            if val is not None:
                current_path.append(val)
                
        # Link elements of this row array together sequentially
        for i in range(len(current_path)):
            parent_tuple = tuple(current_path[:i])
            child_tuple = tuple(current_path[:i+1])
            
            # Use path history to verify uniqueness 
            # (Prevents identical text labels across branches from fusing together incorrectly)
            is_new_node = child_tuple not in seen_nodes
            child_id = get_node_id(child_tuple)
            
            node_label = wrap_node_text(current_path[i])
            
            # FIX 1: Generate the node inside Graphviz ONLY if it's completely new.
            # Removing the duplicate 'else:' blocks ensures Graphviz won't register redundant node definitions.
            if is_new_node:
                # Color code terminal choices (leaves) differently so they pop out
                if i == len(current_path) - 1:
                    dot.node(child_id, label=node_label, fillcolor='#DCFCE7', color='#15803D', fontcolor='#15803D')
                else:
                    dot.node(child_id, label=node_label)
            
            # 2. Add Edge/Arrow connecting parent and child (with strict deduplication)
            if i == 0:
                edge_pair = (root_id, child_id)
            else:
                parent_id = get_node_id(parent_tuple)
                edge_pair = (parent_id, child_id)
                
            # FIX 2: Check edge safety map to strictly guarantee no duplicate links 
            if edge_pair not in seen_edges:
                dot.edge(edge_pair[0], edge_pair[1])
                seen_edges.add(edge_pair)
                
    return dot

# --- APP HEADER & FILE UPLOADER ---
st.title("OBPA Purchase Structure")
st.markdown("Upload your file, select combination criteria, and click Apply to generate a clean, executive-level vertical flow diagram.")

uploaded_file = st.file_uploader("📂 Drop your model output CSV file here", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    try:
        df = pd.read_csv("Model Output.csv")
        st.info("💡 Presenting data from local 'Model Output.csv'. Upload a new file anytime above.")
    except FileNotFoundError:
        st.warning("Please upload a model output CSV file to proceed.")
        st.stop()

df.columns = [c.lower().strip() for c in df.columns]

# Auto-detect context metric and meta-dimension columns
country_col = 'country' if 'country' in df.columns else None
channel_col = 'channel' if 'channel' in df.columns else None
bu_col = 'businessunit' if 'businessunit' in df.columns else ('business_unit' if 'business_unit' in df.columns else None)
region_col = 'region' if 'region' in df.columns else None
score_col = 'score' if 'score' in df.columns else None

known_meta = [country_col, channel_col, bu_col, region_col, score_col]
level_cols = [col for col in df.columns if col not in known_meta]

st.write("---")

# --- CONTROL INPUT GRID FORM ---
st.subheader("🔍 Filter Combination Criteria")

with st.form("filter_form"):
    col1, col2, col3, col4 = st.columns(4)
    df_filtered = df.copy()

    with col1:
        if country_col and not df_filtered.empty:
            opts = sorted(df_filtered[country_col].dropna().unique())
            selected_country = st.selectbox("Country", opts)
            df_filtered = df_filtered[df_filtered[country_col] == selected_country]
        else:
            st.selectbox("Country", ["N/A"], disabled=True)

    with col2:
        if channel_col and not df_filtered.empty:
            opts = sorted(df_filtered[channel_col].dropna().unique())
            selected_channel = st.selectbox("Channel", opts)
            df_filtered = df_filtered[df_filtered[channel_col] == selected_channel]
        else:
            st.selectbox("Channel", ["N/A"], disabled=True)

    with col3:
        if bu_col and not df_filtered.empty:
            opts = sorted(df_filtered[bu_col].dropna().unique())
            selected_bu = st.selectbox("Business Unit", opts)
            df_filtered = df_filtered[df_filtered[bu_col] == selected_bu]
        else:
            st.selectbox("Business Unit", ["N/A"], disabled=True)
            selected_bu = "Model BU"

    with col4:
        if region_col and not df_filtered.empty:
            opts = sorted(df_filtered[region_col].dropna().unique())
            selected_region = st.selectbox("Region", opts)
            df_filtered = df_filtered[df_filtered[region_col] == selected_region]
        else:
            st.selectbox("Region", ["N/A"], disabled=True)

    submitted = st.form_submit_button("🔥 Apply Filters")

# --- ACTIONS ON APPLY SUBMISSION ---
if submitted:
    st.write("---")
    
    # Show the Model Score metric in the right-hand corner split layout
    score_display_col, _ = st.columns([3, 7])
    with score_display_col:
        if not df_filtered.empty and score_col:
            display_score = df_filtered[score_col].iloc[0]
            st.metric(label="📊 Selected Model Score", value=f"{display_score:.6f}")
        else:
            st.metric(label="📊 Selected Model Score", value="N/A")

    st.subheader("🌿 Decision Flow Diagram")

    if df_filtered.empty:
        st.info("No rule sequences match the selected configuration criteria combinations.")
    else:
        # Generate the strict vertical tree diagram centered from Business Unit
        flowchart = generate_business_flowchart(df_filtered, level_cols, selected_bu)
        
        # Render the clean diagram inside Streamlit
        st.graphviz_chart(flowchart, use_container_width=True)