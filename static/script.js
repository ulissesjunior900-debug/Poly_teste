document.addEventListener("DOMContentLoaded", function () {
  console.log("script.js carregado com sucesso!");

  // Botão: Adicionar Título Manual
  const btnAdicionarTitulo = document.getElementById("btnAdicionarTituloAssisao");
  if (btnAdicionarTitulo && !btnAdicionarTitulo.dataset.listenerAdded) {
    btnAdicionarTitulo.addEventListener("click", function () {
      const container = document.getElementById("titulosContainerAssisao");
      const div = document.createElement("div");
      div.className = "row align-items-center mb-2";
      div.innerHTML = `
        <div class="col-7">
          <input type="text" class="form-control" name="titulos[]" placeholder="Título" required>
        </div>
        <div class="col-3">
          <input type="number" step="0.01" min="0" max="100" class="form-control" name="percentuais[]" placeholder="%" required>
        </div>
        <div class="col-2 text-end">
          <button type="button" class="btn btn-outline-danger" onclick="this.closest('.row').remove()">Excluir</button>
        </div>
      `;
      container.appendChild(div);
    });
    btnAdicionarTitulo.dataset.listenerAdded = "true";
  }

  // Botão: Adicionar Títulos Avulsos
  const btnAdicionarAvulsos = document.getElementById("btnAdicionarAvulsosAssisao");
  if (btnAdicionarAvulsos && !btnAdicionarAvulsos.dataset.listenerAdded) {
    btnAdicionarAvulsos.addEventListener("click", function () {
      const titulosText = document.getElementById("titulosAvulsosAssisao").value.trim();
      const percentual = document.getElementById("percentualAvulsosAssisao").value.trim();
      const container = document.getElementById("titulosContainerAssisao");

      if (!titulosText || !percentual) {
        alert("Preencha os títulos e o percentual para adicionar.");
        return;
      }

      const titulos = titulosText.split("\n").filter(t => t.trim() !== "");
      titulos.forEach(titulo => {
        const div = document.createElement("div");
        div.className = "row align-items-center mb-2";
        div.innerHTML = `
          <div class="col-7">
            <input type="text" class="form-control" name="titulos[]" value="${titulo.trim()}" required>
          </div>
          <div class="col-3">
            <input type="number" step="0.01" min="0" max="100" class="form-control" name="percentuais[]" value="${percentual}" required>
          </div>
          <div class="col-2 text-end">
            <button type="button" class="btn btn-outline-danger" onclick="this.closest('.row').remove()">Excluir</button>
          </div>
        `;
        container.appendChild(div);
      });

      document.getElementById("titulosAvulsosAssisao").value = "";
      document.getElementById("percentualAvulsosAssisao").value = "";
    });
    btnAdicionarAvulsos.dataset.listenerAdded = "true";
  }
});

// Função: carregar modal de detalhes do artista
function carregarDetalhesArtistaAssisao(id) {
  fetch(`/detalhes_artista_assisao/${id}`)
    .then(res => res.text())
    .then(html => {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html;
      document.body.appendChild(wrapper);
      const modal = new bootstrap.Modal(wrapper.querySelector('.modal'));
      modal.show();
    });
}

// Função: carregar modal de edição do artista
function carregarEdicaoArtistaAssisao(id) {
  fetch(`/editar_artista_assisao/${id}`)
    .then(res => res.text())
    .then(html => {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html;
      document.body.appendChild(wrapper);

      // Executar scripts embutidos no modal
      wrapper.querySelectorAll('script').forEach(script => {
        const novoScript = document.createElement('script');
        if (script.src) {
          novoScript.src = script.src;
        } else {
          novoScript.textContent = script.textContent;
        }
        document.body.appendChild(novoScript);
      });

      const modal = new bootstrap.Modal(wrapper.querySelector('.modal'));
      modal.show();
    });
}

// Função: descartar cálculo da aba Assisão
function descartarCalculoAssisao() {
  const alertaResultado = document.querySelector('.alert.alert-success');
  const tabelaResultado = document.querySelector('table.table');
  const formResultado = document.querySelector('#formResultadoAssisao');
  const tituloResultado = document.querySelector('h4.mt-4');

  if (alertaResultado) alertaResultado.remove();
  if (tabelaResultado) tabelaResultado.remove();
  if (formResultado) formResultado.remove();
  if (tituloResultado && tituloResultado.textContent.includes('Resultado do Cálculo')) tituloResultado.remove();
}
