def chunk(text:str, max_chars=1200, overlap=150):
    out=[]; i=0
    while i < len(text):
        out.append(text[i:i+max_chars])
        i += max_chars - overlap
    return out
