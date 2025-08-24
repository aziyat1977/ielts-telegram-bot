# Minimal sample to verify flow; regenerate with tools when your PDF is ready
BOOKS = ["Cambridge 12"]
TESTS = ["Test 5"]
PASSAGES = {
    ("Cambridge 12","Test 5","Passage 1"): {
        "title": "The History of Tea (sample)",
        "english": [
            "Tea has shaped cultures and economies across centuries.",
            "From ancient China to modern cafes, it remains a daily ritual."
        ],
        "ru": [
            "Чай сформировал культуры и экономики на протяжении веков.",
            "От древнего Китая до современных кафе — это ежедневный ритуал."
        ],
        "uz": [
            "Choy asrlar davomida madaniyat va iqtisodiyotga ta’sir ko‘rsatgan.",
            "Qadimgi Xitoydan zamonaviy kafe-gacha — bu kundalik marosim."
        ]
    }
}
