from pdf_utils import gerar_pdf_excel

resultado = gerar_pdf_excel(
    template_path="caminho/do/template.xlsx",
    output_dir="pasta/output",
    nome_pdf="Relatório Bartô Galeno",
    dados={
        'valor_eur': 1500.75,
        'cotacao': 5.42,
        'vencimento': '2023-12-15'
    },
    mes_ref=12,
    ano_ref=2023
)

if resultado:
    print(f"PDF gerado com sucesso: {resultado}")
else:
    print("Falha na geração do PDF")