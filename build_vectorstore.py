# build_vectorstore.py
import os
import pickle
import faiss
import numpy as np

os.makedirs("vectorstore", exist_ok=True)

# English docs
docs_en = [
    "Ibtikar is a volunteer-driven initiative uniting Arabic-speaking university students passionate about innovation, technology, and R&D.",
    "The mission of Ibtikar is to empower students and enrich their technical skills through activities that impact their academic and professional lives.",
    "Ibtikar’s vision is to create a leading community of conscious youth who are innovative problem solvers and socially impactful.",
    "The core values of Ibtikar are: Quality, Creativity, Collaboration, Independence, and Excellence.",
    "Ibtikar's journey began in October 2022 with the idea phase, followed by organized operations and public events in 2023.",
    "By March 2024, Ibtikar had over 500 volunteers, 650+ members, and 1000+ beneficiaries from its programs and events.",
    "Key milestones include launching the Arabic Technofest conference, expanding to Syria, and hosting a conference on emerging technologies.",
    "Ibtikar operates several projects like the Technofest platform for student project teams, the 'Mines Tunnel' for academic guidance, and 'FrizzCamps' for interactive online training.",
    "Student activities include educational trips, cultural events, technical competitions, and community service activities.",
    "Student clubs under Ibtikar include AI Development, Open Source AI, Mobile & Web Development, Cybersecurity, Robotics, Medical Tech, Entrepreneurship, and more.",
    "The initiative is structured into academic wings such as Natural Sciences, Informatics, Management & Arts, and Industrial Engineering.",
    "Ibtikar emphasizes building a collaborative technical youth network and increasing opportunities for Arab students in tech competitions and innovation.",
]

# Arabic docs
docs_ar = [
    "ابتكار مبادرة تطوعية تجمع طلاب الجامعات الناطقين بالعربية المهتمين بالابتكار والتقنية والبحث والتطوير.",
    "رسالة ابتكار تمكين الطلاب وتنمية مهاراتهم التقنية عبر أنشطة تؤثر في حياتهم الأكاديمية والمهنية.",
    "رؤية ابتكار تكوين مجتمع رائد من الشباب الواعين المبتكرين أصحاب الأثر الاجتماعي.",
    "القيم الأساسية لابتكار: الجودة والإبداع والتعاون والاستقلالية والتميز.",
    "بدأت رحلة ابتكار في أكتوبر 2022 بمرحلة الفكرة تلتها عمليات منظمة وفعاليات عامة في 2023.",
    "بحلول مارس 2024 ضمت ابتكار أكثر من 500 متطوع و650+ عضوًا و1000+ مستفيد من البرامج والفعاليات.",
    "من المحطات البارزة إطلاق مؤتمر التقنوفست العربي والتوسع إلى سوريا واستضافة مؤتمر للتقنيات الناشئة.",
    "تشغّل ابتكار عدة مشاريع مثل منصة تقنوفست لفرق الطلاب ونفق المناجم للإرشاد الأكاديمي وFrizzCamps للتدريب التفاعلي عبر الإنترنت.",
    "تشمل أنشطة الطلاب رحلات تعليمية وفعاليات ثقافية ومسابقات تقنية وخدمات مجتمعية.",
    "أندية الطلاب تشمل تطوير الذكاء الاصطناعي والمصدر المفتوح وتطوير الويب والجوال والأمن السيبراني والروبوتات والتقنيات الطبية وريادة الأعمال وغيرها.",
    "الهيكل الأكاديمي يشمل أجنحة العلوم الطبيعية والمعلوماتية والإدارة والفنون والهندسة الصناعية.",
    "تركّز ابتكار على بناء شبكة شبابية تقنية تعاونية وزيادة فرص الطلاب العرب في المنافسات التقنية والابتكار.",
]

documents = docs_en + docs_ar

# Save docs
with open("vectorstore/index.pkl", "wb") as f:
    pickle.dump(documents, f)

# Dummy embeddings (replace with real multilingual model later)
np.random.seed(42)
dimension = 384
embeddings = np.random.rand(len(documents), dimension).astype("float32")

index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
faiss.write_index(index, "vectorstore/index.faiss")

print("✅ Offline bilingual vector store built successfully (dummy embeddings).")
