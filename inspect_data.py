import pandas as pd
import glob

# TRT21
trt = pd.concat([pd.read_parquet(f) for f in glob.glob('processos_trt21_enriquecido_*.parquet')], ignore_index=True)
print(f"TRT21: {len(trt)} processos")
print(f"  anos: {sorted(trt['dataajuizamento_dt'].dt.year.dropna().unique())}")
print(f"  municipio_comarca: {trt['municipio_comarca'].value_counts().head(5).to_dict()}")

# TJRN
tj = pd.concat([pd.read_parquet(f) for f in glob.glob('processos_tjrn_saude_*.parquet')], ignore_index=True)
print(f"\nTJRN: {len(tj)} processos")
print(f"  anos: {sorted(tj['dataajuizamento_dt'].dt.year.dropna().unique())}")
print(f"  municipio_comarca: {tj['municipio_comarca'].value_counts().head(5).to_dict()}")
print(f"  tribunal: {tj['tribunal'].unique()}")
print(f"  grau: {tj['grau'].unique()}")
print(f"  classe_nome: {tj['classe_nome'].value_counts().head(3).to_dict()}")
print(f"  assunto_primario_nome: {tj['assunto_primario_nome'].value_counts().head(5).to_dict()}")

# JFRN
jf = pd.concat([pd.read_parquet(f) for f in glob.glob('processos_jfrn_saude_*.parquet')], ignore_index=True)
print(f"\nJFRN: {len(jf)} processos")
print(f"  anos: {sorted(jf['dataajuizamento_dt'].dt.year.dropna().unique())}")
print(f"  municipio_comarca: {jf['municipio_comarca'].value_counts().head(5).to_dict()}")
print(f"  tribunal: {jf['tribunal'].unique()}")
print(f"  grau: {jf['grau'].unique()}")
print(f"  classe_nome: {jf['classe_nome'].value_counts().head(3).to_dict()}")
print(f"  assunto_primario_nome: {jf['assunto_primario_nome'].value_counts().head(5).to_dict()}")

# Common columns
trt_cols = set(trt.columns)
tj_cols = set(tj.columns)
jf_cols = set(jf.columns)
common = trt_cols & tj_cols & jf_cols
print(f"\nCommon columns: {sorted(common)}")
print(f"TRT21-only: {sorted(trt_cols - tj_cols)}")
print(f"TJRN-only: {sorted(tj_cols - trt_cols)}")
