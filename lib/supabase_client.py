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
    
    
#Fixing dashboard date logic via this helper 5/21/26
@st.cache_data(ttl=300)
def get_latest_clean_date() -> str | None:
    """Return the most recent indicator_date where rs_spy_20d has real values.
    Walks back through distinct dates until one has populated RS data.
    Works around PostgREST's 1000-row default cap.
    """
    s = get_client()
    candidates = []
    seen = set()
    offset = 0
    while len(seen) < 30 and offset < 30000:
        batch = (s.table("latest_indicators")
                   .select("indicator_date")
                   .order("indicator_date", desc=True)
                   .range(offset, offset + 999)
                   .execute().data)
        if not batch:
            break
        for r in batch:
            d = r["indicator_date"]
            if d not in seen:
                seen.add(d)
                candidates.append(d)
        offset += 1000
    for d in candidates:
        sample = (s.table("latest_indicators")
                    .select("rs_spy_20d")
                    .eq("indicator_date", d)
                    .limit(100)
                    .execute().data)
        non_null = sum(1 for r in sample if r["rs_spy_20d"] is not None)
        if non_null >= 10:
            return d
    return candidates[0] if candidates else None