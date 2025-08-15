// historico_pagamentos.js
document.addEventListener('DOMContentLoaded', function() {
    // Elementos DOM
    const filtroArtista = document.getElementById('filtroHistoricoArtista');
    const filtroMes = document.getElementById('filtroHistoricoMes');
    const btnFiltrar = document.getElementById('btnFiltrarHistorico');
    const btnAtualizarStatus = document.getElementById('btnAtualizarStatus');
    const listaPagamentos = document.getElementById('listaHistoricoPagamentos');
    const totalPagoElement = document.getElementById('totalPagoHistorico');
    const mensagensDiv = document.getElementById('mensagensHistorico');
    
    // Armazenar todos os pagamentos originalmente carregados
    let todosPagamentos = [];
    
    // Função para atualizar status dos pagamentos agendados
    async function atualizarStatusAgendados() {
        // Salvar o estado original do botão
        const btnOriginalHTML = btnAtualizarStatus.innerHTML;
        const btnOriginalDisabled = btnAtualizarStatus.disabled;
        
        // Mostrar estado de carregamento
        btnAtualizarStatus.disabled = true;
        btnAtualizarStatus.innerHTML = '<span class="loading-spinner"></span> Atualizando...';
        
        try {
            const response = await fetch('/api/atualizar_status_agendados', {
                method: 'POST'
            });
            const data = await response.json();
            
            // Limpar mensagens anteriores
            mensagensDiv.innerHTML = '';
            
            if (data.success) {
                // Exibir mensagens de retorno
                if(data.mensagens && data.mensagens.length > 0) {
                    mensagensDiv.innerHTML = data.mensagens.map(msg => 
                        `<div class="alert alert-warning">${msg}</div>`
                    ).join('');
                }
                
                // Exibir mensagem de sucesso
                if (data.atualizados && data.atualizados.length > 0) {
                    mensagensDiv.innerHTML += `<div class="alert alert-success">${data.atualizados.length} pagamentos atualizados para "Pago".</div>`;
                } else {
                    mensagensDiv.innerHTML += `<div class="alert alert-info">Nenhum pagamento agendado precisou ser atualizado.</div>`;
                }
                
                // Recarregar dados atualizados
                await carregarHistorico();
            } else {
                mensagensDiv.innerHTML = `<div class="alert alert-danger">Erro: ${data.error}</div>`;
            }
        } catch (error) {
            console.error('Erro na requisição:', error);
            mensagensDiv.innerHTML = `<div class="alert alert-danger">Erro de conexão com o servidor</div>`;
        } finally {
            // Restaurar estado do botão
            btnAtualizarStatus.disabled = btnOriginalDisabled;
            btnAtualizarStatus.innerHTML = btnOriginalHTML;
        }
    }

    // Função para carregar histórico
    async function carregarHistorico() {
        try {
            const response = await fetch('/api/historico_pagamentos');
            const data = await response.json();
            
            if(data.success) {
                todosPagamentos = data.pagamentos;
                aplicarFiltros();
            } else {
                mensagensDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
            mensagensDiv.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados</div>`;
        }
    }

    // Função para aplicar filtros na tabela
    function aplicarFiltros() {
        const artista = filtroArtista.value.toLowerCase();
        const mes = filtroMes.value;
        
        const pagamentosFiltrados = todosPagamentos.filter(pagamento => {
            const matchArtista = artista ? 
                (pagamento.artista_nome || '').toLowerCase().includes(artista) : true;
                
            const matchMes = mes ? 
                pagamento.mes_abreviado === mes : true;
                
            return matchArtista && matchMes;
        });
        
        montarTabelaHistorico(pagamentosFiltrados);
        atualizarTotalPago(pagamentosFiltrados);
    }

    // Função para atualizar o total pago
    function atualizarTotalPago(pagamentos) {
        const total = pagamentos.reduce((sum, pag) => {
            return pag.status.toLowerCase() === 'pago' ? sum + pag.valor_brl : sum;
        }, 0);
        
        totalPagoElement.textContent = `R$ ${total.toFixed(2).replace('.', ',')}`;
    }

    // Função para montar tabela de histórico
    function montarTabelaHistorico(pagamentos) {
        listaPagamentos.innerHTML = '';
        
        if (pagamentos.length === 0) {
            listaPagamentos.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-3">
                        Nenhum pagamento encontrado
                    </td>
                </tr>
            `;
            return;
        }
        
        pagamentos.forEach(pag => {
            const tr = document.createElement('tr');
            
            // Determina a classe do badge conforme o status
            let badgeClass = 'bg-secondary';
            let statusText = pag.status;
            if (pag.status.toLowerCase() === 'pago') {
                badgeClass = 'bg-success';
                statusText = 'Pago';
            } else if (pag.status.toLowerCase() === 'agendado') {
                badgeClass = 'bg-warning text-dark';
                statusText = 'Agendado';
            }
            
            // Formatar data de vencimento
            const dataFormatada = pag.vencimento ? 
                new Date(pag.vencimento).toLocaleDateString('pt-BR') : '-';
            
            tr.innerHTML = `
                <td>${dataFormatada}</td>
                <td>${pag.artista_nome || 'Artista não identificado'}</td>
                <td>${pag.mes}/${pag.ano}</td>
                <td class="text-end">R$ ${pag.valor_brl.toFixed(2).replace('.', ',')}</td>
                <td><span class="badge ${badgeClass} badge-status">${statusText}</span></td>
            `;
            listaPagamentos.appendChild(tr);
        });
    }

    // Função para limpar filtros
    function limparFiltros() {
        filtroArtista.value = '';
        filtroMes.value = '';
        aplicarFiltros();
    }

    // Event Listeners
    btnFiltrar.addEventListener('click', aplicarFiltros);
    btnAtualizarStatus.addEventListener('click', atualizarStatusAgendados);
    
    // Adicionar evento para limpar filtros ao clicar no título
    const cardHeader = document.querySelector('.card-header');
    if (cardHeader) {
        cardHeader.addEventListener('dblclick', limparFiltros);
    }
    
    // Inicialização
    carregarHistorico();
});