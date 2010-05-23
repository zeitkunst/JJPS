"""Text processing methods used by other modules."""

# External library imports
import nltk

def tokenize(text, clean = True):
    """Helper function to tokenize our input text."""
    tokens = []
    sentences = nltk.sent_tokenize(text)
    for sentence in sentences:
        words = nltk.word_tokenize(sentence)
        for word in words:
            tokens.append(word)

    # If we want to get rid of punctuation...
    if (clean):
        clean_tokens = []
        for token in tokens:
            if len(token) < 2: # Only save words longer than 2 chars
                continue
            clean_tokens.append(token.lower()) # Always lower case
        return clean_tokens

    else:
        # Or just get everything, in lowercase of course
        clean_tokens = []
        for token in tokens:
            clean_tokens.append(token.lower())
        return clean_tokens


def get_term_freq(tokens):
    tf = {}
    for token in tokens:
        if token not in tf:
            tf[token] = float(tokens.count(token))/float(len(tokens))
    return tf
