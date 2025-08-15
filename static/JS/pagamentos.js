// pagamentos.js

document.addEventListener('DOMContentLoaded', function() {
    // Elementos principais
    const btnCalcular = document.getElementById('btnCalcularResumo');
    const checkboxes = document.querySelectorAll('.calculo-checkbox');
    const checkboxRetencao = document.getElementById('checkboxRetencao');
    const inputPercentualRetencao = document.getElementById('inputPercentualRetencao');
    const checkboxHerdeiro = document.getElementById('checkboxHerdeiro');
    const inputPercentualHerdeiro = document.getElementById('inputPercentualHerdeiro');
    const resumoSP = document.getElementById('resumoSP');
    const btnAgendar = document.getElementById('btnAgendarPagamento');
    const btnGerarExcel = document.getElementById('formGerarExcel');
    const btnGerarPDF = document.getElementById('btnGerarSP');
    const formGerarPDF = document.getElementById('formGerarPDF');
    const vencimentoInput = document.getElementById('vencimentoInput');
    const cotacaoSelect = document.getElementById('cotacaoSelect');
    const spSelect = document.getElementById('spSelect');
    const artistaSelect = document.getElementById('artistaSelect');
    
    // Elementos do histórico
    const btnAtualizarHistorico = document.querySelector('.btn-outline-primary');
    const filtroArtista = document.querySelector('.filtros-container select:first-child');
    const filtroStatus = document.querySelector('.filtros-container select:nth-child(2)');
    const btnFiltrar = document.querySelector('.filtros-container .btn-primary');
    
    // Ferramentas de diagnóstico
    const btnResetAgendamento = document.getElementById('btnResetAgendamento');
    const btnSimularErro = document.getElementById('btnSimularErro');
    const btnVerDados = document.getElementById('btnVerDados');
    
    // Dados dos cálculos (injetado pelo template)
    const calculos = todosCalculos;
    
    // Relatório de testes
    const relatorioTestes = [];
    
    // =====================
    // FUNÇÕES PRINCIPAIS
    // =====================
    
    // Obter cálculos selecionados
    function getCalculosSelecionados() {
        return Array.from(checkboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => {
                const [origem, id] = checkbox.value.split('_');
                return {
                    id: parseInt(id),
                    origem,
                    valorEur: parseFloat(checkbox.dataset.valorEur),
                    mes: parseInt(checkbox.dataset.mes),
                    ano: parseInt(checkbox.dataset.ano),
                    artista: checkbox.dataset.artista
                };
            });
    }
    
    // Verificar status dos cálculos
    async function verificarStatusCalculos() {
        const calculosSelecionados = getCalculosSelecionados();
        
        if (calculosSelecionados.length === 0) {
            return { hasProcessed: false };
        }

        try {
            const response = await fetch('/api/verificar_status_calculos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    calculos_ids: calculosSelecionados.map(c => c.id)
                })
            });

            return await response.json();
        } catch (error) {
            console.error('Erro ao verificar status:', error);
            return { hasProcessed: false };
        }
    }
    
    // Calcular resumo profissional
    async function calcularResumo() {
        const statusCheck = await verificarStatusCalculos();
        
        if (statusCheck.hasProcessed) {
            const confirmar = confirm(`ATENÇÃO: Alguns cálculos já foram processados (${statusCheck.processedItems.join(', ')}).\nDeseja continuar mesmo assim?`);
            
            if (!confirmar) {
                statusCheck.processedIds.forEach(id => {
                    const checkbox = document.querySelector(`.calculo-checkbox[value*="_${id}"]`);
                    if (checkbox) checkbox.checked = false;
                });
                return;
            }
        }
        
        const calculosSelecionados = getCalculosSelecionados();
        
        if (calculosSelecionados.length === 0) {
            resumoSP.innerHTML = `
                <div class="text-center text-muted py-4 grid-col-span-2">
                    <i class="bi bi-exclamation-triangle me-2"></i> Selecione pelo menos um cálculo
                </div>
            `;
            return;
        }

        // Calcular totais
        const totalEur = calculosSelecionados.reduce((sum, calc) => sum + calc.valorEur, 0);
        const cotacao = parseFloat(cotacaoSelect.value) || 5.5;
        const totalBRL = totalEur * cotacao;
        
        // Aplicar retenção ISS
        let valorRetencao = 0;
        let valorLiquido = totalBRL;
        const percRetencao = inputPercentualRetencao.value ? parseFloat(inputPercentualRetencao.value) : 0;
        
        if (checkboxRetencao.checked && percRetencao > 0) {
            valorRetencao = totalBRL * (percRetencao / 100);
            valorLiquido = totalBRL - valorRetencao;
        }
        
        // Aplicar percentual para herdeiro
        const percHerdeiro = inputPercentualHerdeiro.value ? parseFloat(inputPercentualHerdeiro.value) : 0;
        if (checkboxHerdeiro.checked && percHerdeiro > 0) {
            valorLiquido = valorLiquido * (percHerdeiro / 100);
        }

        // Encontrar o artista principal
        const artistasCount = {};
        calculosSelecionados.forEach(calc => {
            artistasCount[calc.artista] = (artistasCount[calc.artista] || 0) + 1;
        });
        const artistaPrincipal = Object.keys(artistasCount).reduce((a, b) => 
            artistasCount[a] > artistasCount[b] ? a : b
        );

        // Encontrar o período mais recente
        const periodoMaisRecente = calculosSelecionados.reduce((recente, calc) => {
            const calcDate = new Date(calc.ano, calc.mes - 1);
            return calcDate > recente ? calcDate : recente;
        }, new Date(0));

        const mes = periodoMaisRecente.getMonth() + 1;
        const ano = periodoMaisRecente.getFullYear();
        const meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
        
        // Atualizar resumo com layout profissional
        resumoSP.innerHTML = `
            <div class="resumo-item">
                <span class="resumo-label">Artista</span>
                <span class="resumo-value">${artistaPrincipal}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Período de Referência</span>
                <span class="resumo-value">${meses[mes]} ${ano}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Total em Euros (€)</span>
                <span class="resumo-value">€ ${totalEur.toFixed(4)}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Cotação (R$/€)</span>
                <span class="resumo-value">R$ ${cotacao.toFixed(4)}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Total em Reais (R$)</span>
                <span class="resumo-value">R$ ${totalBRL.toFixed(2)}</span>
            </div>
            
            ${percRetencao > 0 ? `
            <div class="resumo-item">
                <span class="resumo-label">Retenção ISS (${percRetencao}%)</span>
                <span class="resumo-value text-danger">- R$ ${valorRetencao.toFixed(2)}</span>
            </div>` : ''}
            
            ${percHerdeiro > 0 ? `
            <div class="resumo-item">
                <span class="resumo-label">Percentual Herdeiro (${percHerdeiro}%)</span>
                <span class="resumo-value">R$ ${(totalBRL - valorRetencao).toFixed(2)}</span>
            </div>` : ''}
            
            <div class="resumo-divider"></div>
            
            <div class="resumo-total">
                <span class="resumo-label">VALOR LÍQUIDO</span>
                <span class="resumo-value">R$ ${valorLiquido.toFixed(2)}</span>
            </div>
        `;

        // Atualizar campos ocultos
        document.getElementById('spIdHidden').value = spSelect.value;
        document.getElementById('spIdPDF').value = spSelect.value;
        document.getElementById('calculosIdsHiddenForm').value = calculosSelecionados.map(c => `${c.origem}_${c.id}`).join(',');
        document.getElementById('calculosPDF').value = calculosSelecionados.map(c => `${c.origem}_${c.id}`).join(',');
        document.getElementById('valorEurHiddenForm').value = totalEur;
        document.getElementById('valorEurPDF').value = totalEur;
        document.getElementById('cotacaoHiddenForm').value = cotacao;
        document.getElementById('cotacaoPDF').value = cotacao;
        document.getElementById('retencaoHiddenForm').value = percRetencao;
        document.getElementById('retencaoPDF').value = percRetencao;
        document.getElementById('mesPDF').value = mes;
        document.getElementById('anoPDF').value = ano;
        document.getElementById('artistaNomePDF').value = artistaPrincipal;
    }
            
    // Mostrar notificação toast
    function showToast(type, title, message) {
        const toastContainer = document.createElement('div');
        toastContainer.className = `toast align-items-center text-white bg-${type} border-0`;
        toastContainer.setAttribute('role', 'alert');
        toastContainer.setAttribute('aria-live', 'assertive');
        toastContainer.setAttribute('aria-atomic', 'true');
        
        toastContainer.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        document.body.appendChild(toastContainer);
        
        const toast = new bootstrap.Toast(toastContainer, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        toastContainer.addEventListener('hidden.bs.toast', () => {
            toastContainer.remove();
        });
    }
    
    // Registrar evento de teste
    function registrarEventoTeste(acao, detalhes, status = 'Simulado') {
        const evento = {
            timestamp: new Date().toISOString(),
            acao,
            detalhes,
            status
        };
        
        relatorioTestes.push(evento);
        
        if (relatorioTestes.length > 50) {
            relatorioTestes.shift();
        }
    }
    
    // =====================
    // EVENT LISTENERS
    // =====================
    
    // Eventos principais
    btnCalcular.addEventListener('click', calcularResumo);
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', calcularResumo);
    });
    
    checkboxRetencao.addEventListener('change', function() {
        inputPercentualRetencao.disabled = !this.checked;
        calcularResumo();
    });
    
    checkboxHerdeiro.addEventListener('change', function() {
        inputPercentualHerdeiro.disabled = !this.checked;
        calcularResumo();
    });
    
    inputPercentualRetencao.addEventListener('input', calcularResumo);
    inputPercentualHerdeiro.addEventListener('input', calcularResumo);
    cotacaoSelect.addEventListener('change', calcularResumo);
    spSelect.addEventListener('change', calcularResumo);
    artistaSelect.addEventListener('change', calcularResumo);
    
    btnAgendar.addEventListener('click', toggleAgendamento);
    
    vencimentoInput.addEventListener('change', function() {
        document.getElementById('vencimentoInputHidden').value = this.value;
        document.getElementById('vencimentoPDF').value = this.value;
    });
    
    btnGerarPDF.addEventListener('click', function() {
        if (!vencimentoInput.value) {
            alert('Por favor, selecione uma data de vencimento');
            vencimentoInput.focus();
            return;
        }
        formGerarPDF.submit();
    });
    
function toggleAgendamento() {
    const statusAtual = btnAgendar.dataset.status;
    
    if (statusAtual === 'aguardando') {
        // Alterar para Agendado
        btnAgendar.dataset.status = 'agendado';
        btnAgendar.classList.remove('btn-agendar');
        btnAgendar.classList.add('btn-agendado');
        btnAgendar.innerHTML = '<i class="bi bi-clock-history me-1"></i> Agendado';
        document.getElementById('statusPagamentoHidden').value = 'Agendado';

        showToast('success', 'Agendamento', 'Cálculo agendado com sucesso');
    } else {
        // Voltar para Aguardando
        btnAgendar.dataset.status = 'aguardando';
        btnAgendar.classList.remove('btn-agendado');
        btnAgendar.classList.add('btn-agendar');
        btnAgendar.innerHTML = '<i class="bi bi-calendar-check me-1"></i> Agendar';
        document.getElementById('statusPagamentoHidden').value = 'Aguardando';

        showToast('info', 'Agendamento cancelado', 'Status retornado para aguardando');
    }
}

    // Eventos do histórico

async function salvarCalculoNoHistorico(dadosCalculo) {
  try {
    const res = await fetch('/salvar_calculo_pagamento', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
      },
      body: JSON.stringify(dadosCalculo)
    });
    const data = await res.json();
    if (data.success) {
      showToast('success', 'Histórico', 'Cálculo salvo no histórico');
      atualizarHistorico();  // atualizar lista após salvar
    } else {
      showToast('danger', 'Erro', data.error);
    }
  } catch (err) {
    showToast('danger', 'Erro', 'Falha na requisição');
  }
}

    
// Ferramentas de diagnóstico
document.addEventListener("DOMContentLoaded", function () {
    const btnResetAgendamento = document.getElementById('btnResetAgendamento');
    const btnSimularErro = document.getElementById('btnSimularErro');
    const btnAgendar = document.getElementById('btnAgendar');
    const vencimentoInput = document.getElementById('vencimentoInput');

    if (btnResetAgendamento && btnAgendar && vencimentoInput) {
        btnResetAgendamento.addEventListener('click', function() {
            btnAgendar.dataset.status = 'aguardando';
            btnAgendar.classList.remove('btn-agendado');
            btnAgendar.classList.add('btn-agendar');
            btnAgendar.innerHTML = '<i class="bi bi-calendar-check me-1"></i> Agendar';
            vencimentoInput.value = '';
            showToast('info', 'Agendamento resetado', 'Status foi redefinido para aguardando');
            registrarEventoTeste('Reset Agendamento', 'Status resetado manualmente');
        });
    }

    if (btnSimularErro) {
        btnSimularErro.addEventListener('click', function() {
            showToast('danger', 'Erro simulado', 'Esta é uma simulação de erro para testes');
            registrarEventoTeste('Erro Simulado', 'Usuário solicitou simulação de erro', 'Erro');
        });
    }
});
    
document.addEventListener("DOMContentLoaded", function () {
    const btnVerDados = document.getElementById('btnVerDados');
    const btnAgendar = document.getElementById('btnAgendar');
    const vencimentoInput = document.getElementById('vencimentoInput');
    const inputPercentualRetencao = document.getElementById('inputPercentualRetencao');
    const inputPercentualHerdeiro = document.getElementById('inputPercentualHerdeiro');

    if (btnVerDados && btnAgendar && vencimentoInput && inputPercentualRetencao && inputPercentualHerdeiro) {
        btnVerDados.addEventListener('click', function () {
            const calculosSelecionados = getCalculosSelecionados();
            const dados = {
                agendamento: btnAgendar.dataset.status,
                vencimento: vencimentoInput.value,
                calculos: calculosSelecionados,
                retencao: inputPercentualRetencao.value,
                herdeiro: inputPercentualHerdeiro.value
            };

            alert('Dados atuais:\n' + JSON.stringify(dados, null, 2));
            registrarEventoTeste('Ver Dados', 'Visualização dos dados selecionados');
        });
    }
});
    
    // Registrar eventos nas ações importantes
    btnAgendar.addEventListener('click', () => {
        const status = btnAgendar.dataset.status === 'aguardando' ? 'Agendado' : 'Aguardando';
        registrarEventoTeste(
            status === 'Agendado' ? 'Agendamento' : 'Cancelamento de Agendamento',
            `Status alterado para: ${status}`
        );
    });
    
    btnGerarExcel.addEventListener('submit', () => {
        registrarEventoTeste('Geração de Excel', 'Documento Excel gerado para download');
    });
    
btnGerarPDF.addEventListener('click', () => {
    registrarEventoTeste('Geração de PDF', 'Documento PDF gerado para download');

    const inputOriginal = document.getElementById('inputAnexosPDF');
    const inputForm = document.getElementById('inputAnexosForm');
    const vencimentoInput = document.getElementById('vencimentoInput');

    if (!vencimentoInput.value) {
        alert('Por favor, selecione uma data de vencimento');
        vencimentoInput.focus();
        return;
    }

    // Copiar arquivos para o form oculto se existirem
    if (inputOriginal && inputForm && inputOriginal.files.length > 0) {
        const dataTransfer = new DataTransfer();
        for (let file of inputOriginal.files) {
            dataTransfer.items.add(file);
        }
        inputForm.files = dataTransfer.files;
    }

    formGerarPDF.submit();
});

    
    // Inicialização
    inputPercentualRetencao.disabled = !checkboxRetencao.checked;
    inputPercentualHerdeiro.disabled = !checkboxHerdeiro.checked;

});