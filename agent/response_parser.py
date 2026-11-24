def label_output(text):return {'text':text,'contains_human_review':'human review' in text.lower(),'contains_sources':'source' in text.lower()}
