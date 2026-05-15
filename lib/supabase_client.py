"""Cached Supabase client for the dashboard."""

import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_client() -> Client:
    """
    Returns a cached Supabase client. The @st.cache_resource decorator
    means this client is created once per session and reused across
    all queries — much better than creating a new client per query.
    """
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )