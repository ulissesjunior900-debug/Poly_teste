import csv

# Inicializa o total
total_lucro_liquido = 0.0

with open('2019 - JAN - MAR POLYDISC.csv', 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file, delimiter=';', quotechar='"')
    
    for row in reader:
        # Verifica se o artista é "Cyro Aguiar" (nome do artista, não da etiqueta!)
        if row['Nome do artista'] == 'Cyro Aguiar':
            # Converte o "Lucro Líquido" de string para float (substitui vírgula por ponto)
            lucro = float(row['Lucro Líquido'].replace(',', '.'))
            total_lucro_liquido += lucro

# Formata o resultado para 2 casas decimais
print(f"Total do Lucro Líquido para Cyro Aguiar: €{total_lucro_liquido:.2f}")