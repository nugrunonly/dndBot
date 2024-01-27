import re


def ascii_sanitize(text):
    return text.encode('ascii', errors='ignore').decode()

def split_response(response, max_length=500):
    # Base case: if the response is short enough, return it in a list.
    if len(response) <= max_length:
        return [response]
    else:
        # Try to find the last sentence break within the maximum length.
        sentence_end_positions = [m.end() for m in re.finditer(r'[.!?]', response[:max_length])]
        if sentence_end_positions:
            sentence_end = max(sentence_end_positions)
        else:
            # If no sentence break is found, just cut at the maximum length.
            sentence_end = max_length
        # Recursively split the rest of the response.
        return [response[:sentence_end].strip()] + split_response(response[sentence_end:].strip(), max_length)