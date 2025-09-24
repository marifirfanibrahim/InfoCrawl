# model_save.py
from gliner import GLiNER

# load and save
model = GLiNER.from_pretrained("urchade/gliner_multi")
model.save_pretrained("model/gliner_multi")

loaded_model = GLiNER.from_pretrained("model/gliner_multi", load_tokenizer = True, local_files_only=True)

# test
text = """
Pada Ahad, seorang pengusaha pusat latihan komputer tergolak apabila rumah kedai miliknya terbakar di
 Kampung Alor Pasir, Pasir Puteh. Pemburu bahaya mengaku tidak sempat menyelamatkan semua barangan miliknya 
 kerana api marak dengan begitu cepat.
"""

labels = [
    "GPE", "PERSON", "ORG", "FAC", "MONEY", "NORP", "LOC", "PRODUCT", "EVENT",
    "PERCENT", "WORK_OF_ART", "TIME", "ORDINAL", "CARDINAL", "QUANTITY", "LAW"
]

entities = loaded_model.predict_entities(text, labels, threshold=0.4)

for entity in entities:
    print(entity["text"], "=>", entity["label"])