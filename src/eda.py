import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

DATA_PATH = "../data/"

# 1) 데이터 로드
courses = pd.read_csv(DATA_PATH + "courses.csv")
assessments = pd.read_csv(DATA_PATH + "assessments.csv")
vle = pd.read_csv(DATA_PATH + "vle.csv")
student_info = pd.read_csv(DATA_PATH + "studentInfo.csv")
student_registration = pd.read_csv(DATA_PATH + "studentRegistration.csv")
student_assessment = pd.read_csv(DATA_PATH + "studentAssessment.csv")
student_vle = pd.read_csv(DATA_PATH + "studentVle.csv")

# 2) 테이블로 한번에 핸들링할 예정
tables = {
    "courses": courses,
    "assessments": assessments,
    "vle": vle,
    "student_info": student_info,
    "student_registration": student_registration,
    "student_assessment": student_assessment,
    "student_vle": student_vle
}

# 테이블 크기 재확인
print("#### The size of each dataset ####\n")
for name, df in tables.items():
    print(name, df.shape)

# 3) 결측치 확인
print("#### Missing value check ####\n")
for name, df in tables.items():
    print(f"\nMissing values in {name}")
    print(df.isna().sort_values(ascending=False).head(10))

# 4) target distribution 확인
print(student_info["final_result"].value_counts(dropna=False))
student_info["final_result"].value_counts()
student_info["final_result"].value_counts(normalize=True)
sns.countplot(data=student_info, x="final_result")
plt.title("Distribution of Final Result")
plt.show()

# 5) 동일 학생-과목-회차가 중복되는지 확인 (데이터 id의 유일성 점검)
KEY = ["code_module", "code_presentation", "id_student"]
# 한 학생당 반드시 한행이어야 함
print(f"student_info duplication check : {student_info.duplicated(KEY).sum()}")
print(f"student_registration duplication check : {student_registration.duplicated(KEY).sum()}")