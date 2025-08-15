// exportar_planilhas.js - Versão Corrigida

document.addEventListener('DOMContentLoaded', function () {
    // ELEMENTOS
    const artistOptions = document.getElementById('artistOptions');
    const artistSearch = document.getElementById('artistSearch');
    const btnNext = document.getElementById('btnNext');
    const btnBack = document.getElementById('btnBack');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const reportOptions = document.getElementById('reportOptions');
    const confirmationDetails = document.getElementById('confirmationDetails');
    const btnExport = document.getElementById('btnExport');
    const exportFormats = document.querySelectorAll('.export-format');
    const successModal = document.getElementById('successModal');
    const modalClose = document.getElementById('modalClose');
    const downloadNow = document.getElementById('downloadNow');
    const dateRangeSection = document.getElementById('dateRangeSection');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');

    // VARIÁVEIS DE ESTADO
    let selectedArtist = null;
    let selectedReport = null;
    let selectedFormat = null;

    // ==== FUNÇÕES ====

    async function fetchArtists() {
        try {
            const response = await axios.get('/api/artistas');
            renderArtists(response.data);
        } catch (error) {
            console.error('Erro ao buscar artistas:', error);
            artistOptions.innerHTML = '<p class="text-red-500">Erro ao carregar artistas.</p>';
        }
    }

    function renderArtists(artists) {
        artistOptions.innerHTML = '';
        if (!artists || !artists.length) {
            artistOptions.innerHTML = '<p class="text-gray-500">Nenhum artista encontrado.</p>';
            return;
        }

        artists.forEach(artist => {
            const card = document.createElement('div');
            card.className = `artist-card cursor-pointer border rounded-lg p-4 w-48 text-center hover:bg-indigo-50 transition duration-200 ${
                selectedArtist && selectedArtist.id === artist.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'
            }`;
            card.innerHTML = `
                <div class="text-indigo-600 text-3xl mb-2">
                    <i class="fas fa-user-circle"></i>
                </div>
                <h3 class="font-semibold text-gray-800 mb-1">${artist.nome}</h3>
                <p class="text-sm text-gray-500">${artist.albums} álbuns • ${artist.songs} músicas</p>
            `;

            card.addEventListener('click', () => {
                selectedArtist = artist;
                renderArtists(artists);
                updateNextButtonState();
            });

            artistOptions.appendChild(card);
        });
    }

    function updateNextButtonState() {
        if (step1.classList.contains('hidden')) {
            // Passo 2 (seleção de relatório)
            btnNext.disabled = !selectedReport;
        } else {
            // Passo 1 (seleção de artista)
            btnNext.disabled = !selectedArtist;
        }
    }

    function updateConfirmationDetails() {
        if (!selectedArtist || !selectedReport) {
            confirmationDetails.innerHTML = '<p class="text-red-500">Informações incompletas.</p>';
            return;
        }

        confirmationDetails.innerHTML = `
            <p><strong>Artista:</strong> ${selectedArtist.nome}</p>
            <p><strong>Planilha:</strong> ${selectedReport.name}</p>
            <p><strong>Detalhes:</strong> ${selectedReport.description}</p>
            ${
                selectedReport.requiresDate
                    ? `<p><strong>Período:</strong> ${startDate.value || '---'} até ${endDate.value || '---'}</p>`
                    : ''
            }
        `;
    }

    async function exportReport() {
        if (!selectedArtist || !selectedReport || !selectedFormat) {
            alert('Selecione um formato de exportação.');
            return;
        }

        try {
            const payload = {
                artist_id: selectedArtist.id,
                report_id: selectedReport.id,
                format: selectedFormat,
                start_date: startDate.value || null,
                end_date: endDate.value || null
            };

            const response = await axios.post('/api/exportar', payload, {
                responseType: 'blob'
            });

            const blob = new Blob([response.data]);
            const url = window.URL.createObjectURL(blob);
            downloadNow.setAttribute('href', url);
            downloadNow.setAttribute('download', `relatorio_${selectedReport.name.split('.')[0]}.${selectedFormat}`);

            successModal.classList.remove('hidden');

        } catch (error) {
            console.error('Erro ao exportar relatório:', error);
            alert('Erro ao exportar a planilha. Detalhes: ' + (error.response?.data?.message || error.message));
        }
    }

    // ==== EVENTOS ====

    btnNext.addEventListener('click', () => {
        if (step1.classList.contains('hidden')) {
            // Passo 2 → Passo 3
            if (!selectedReport) {
                alert('Selecione uma planilha.');
                return;
            }

            step2.classList.add('hidden');
            step3.classList.remove('hidden');
            btnNext.classList.add('hidden');
            btnExport.classList.remove('hidden');
            btnBack.classList.remove('hidden');
            updateConfirmationDetails();

        } else {
            // Passo 1 → Passo 2
            if (!selectedArtist) {
                alert('Selecione um artista.');
                return;
            }

            step1.classList.add('hidden');
            step2.classList.remove('hidden');
            btnBack.classList.remove('hidden');

            // NÃO BUSCA VIA API — planilhas já renderizadas no HTML
            // fetchReports(); ← Removido conforme solicitado
        }
    });

    btnBack.addEventListener('click', () => {
        if (!step3.classList.contains('hidden')) {
            // Passo 3 → Passo 2
            step3.classList.add('hidden');
            step2.classList.remove('hidden');
            btnExport.classList.add('hidden');
            btnNext.classList.remove('hidden');
        } else if (!step2.classList.contains('hidden')) {
            // Passo 2 → Passo 1
            step2.classList.add('hidden');
            step1.classList.remove('hidden');
            btnBack.classList.add('hidden');
        }
        updateNextButtonState();
    });

    exportFormats.forEach(button => {
        button.addEventListener('click', () => {
            selectedFormat = button.getAttribute('data-format');
            exportReport();
        });
    });

    modalClose.addEventListener('click', () => {
        successModal.classList.add('hidden');
    });

    downloadNow.addEventListener('click', () => {
        successModal.classList.add('hidden');
    });

    artistSearch.addEventListener('input', async (e) => {
        try {
            const response = await axios.get('/api/artistas', {
                params: {
                    q: e.target.value
                }
            });
            renderArtists(response.data);
        } catch (error) {
            console.error('Erro ao buscar artistas:', error);
        }
    });

    // ==== INICIALIZAÇÃO ====
    fetchArtists();
    updateNextButtonState();
});