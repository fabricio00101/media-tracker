const filterBtns = document.querySelectorAll(".filter-btn");
      const qualityInput = document.getElementById("quality_tag");
      const visibleMinSize = document.getElementById("visible_min_size");
      const hiddenMinSize = document.getElementById("min_size_gb");

      // --- Escapado de HTML ---
      // Los títulos, sinopsis y trackers provienen de Prowlarr (datos externos),
      // por lo que NUNCA deben insertarse sin escapar en innerHTML.
      const escapeHtml = (value) =>
        String(value ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");

      // Codifica un objeto para transportarlo en un atributo data-*
      const encodeData = (value) => encodeURIComponent(JSON.stringify(value));

      // --- Indicador de carga global (barra superior) ---
      const globalProgressBar = document.createElement("div");
      globalProgressBar.className =
        "fixed top-0 left-0 h-1 bg-violet-500 z-[60] transition-all duration-300 opacity-0 w-0";
      document.body.appendChild(globalProgressBar);

      const showGlobalLoader = () => {
        globalProgressBar.classList.remove("opacity-0");
        globalProgressBar.style.width = "70%";
      };

      const hideGlobalLoader = () => {
        globalProgressBar.style.width = "100%";
        setTimeout(() => {
          globalProgressBar.classList.add("opacity-0");
          globalProgressBar.style.width = "0";
        }, 300);
      };

      // --- Control de búsquedas concurrentes (evita condiciones de carrera) ---
      let searchSequence = 0;
      let activeSearchController = null;
      
      // ESTADO GLOBAL
      let globalCurrentResults = [];
      let globalRenderedCount = 0;
      const RESULTS_PER_PAGE = 16;
      // localStorage puede estar corrupto: nunca debe romper el arranque de la página
      const loadFavorites = () => {
          try {
              const raw = localStorage.getItem('mt_favorites');
              const parsed = raw ? JSON.parse(raw) : [];
              return Array.isArray(parsed) ? parsed : [];
          } catch (err) {
              console.warn('Favoritos no legibles, se reinician:', err);
              return [];
          }
      };
      let favorites = loadFavorites();

      // Datos crudos de la última búsqueda (para exportar)
      let globalRawResults = [];
      let globalLastQuery = "";

      // Estado de paginación server-side
      let globalPage = 1;
      let globalHasMore = false;
      let globalTotalGroups = 0;
      let globalSearchParams = null;
      let globalLoadingMore = false;

      // Funciones de Favoritos
      const saveFavorites = () => {
          try {
              localStorage.setItem('mt_favorites', JSON.stringify(favorites));
          } catch (err) {
              console.warn('No se pudieron guardar los favoritos:', err);
          }
      };
      
      // Recibe el objeto info directamente: nunca se interpola en HTML
      const toggleFavorite = (groupKey, groupInfo) => {
          const idx = favorites.findIndex(f => f.key === groupKey);
          
          if (idx > -1) {
              favorites.splice(idx, 1);
          } else {
              favorites.push({
                  key: groupKey,
                  info: groupInfo,
                  added_at: new Date().toISOString()
              });
          }
          saveFavorites();
          renderFavorites();
          
          // Actualizar botón en el dom principal si existe
          const btn = document.querySelector(`.fav-btn[data-key="${CSS.escape(groupKey)}"]`);
          if(btn) updateFavBtnVisual(btn, idx === -1);
      };
      
      const updateFavBtnVisual = (btn, isFav) => {
          if(isFav) {
              btn.innerHTML = '<i class="fas fa-heart"></i>';
              btn.classList.add('text-red-500');
              btn.classList.remove('text-gray-400');
          } else {
              btn.innerHTML = '<i class="far fa-heart"></i>';
              btn.classList.remove('text-red-500');
              btn.classList.add('text-gray-400');
          }
      };

      const renderFavorites = () => {
          const container = document.getElementById('favoritesList');
          const emptyMsg = document.getElementById('emptyFavoritesMessage');
          container.innerHTML = '';
          
          if (favorites.length === 0) {
              emptyMsg.classList.remove('hidden');
              return;
          }
          emptyMsg.classList.add('hidden');
          
          favorites.sort((a,b) => new Date(b.added_at) - new Date(a.added_at)).forEach(fav => {
              const info = fav.info;
              const posterImg = info.poster_url
                ? `<img src="${escapeHtml(info.poster_url)}" alt="${escapeHtml(info.title)}" class="w-24 h-36 object-cover rounded-lg shadow-md flex-shrink-0">`
                : `<div class="w-24 h-36 bg-gray-800 rounded-lg shadow-md flex-shrink-0 flex items-center justify-center"><i class="fas fa-film text-3xl text-gray-600"></i></div>`;
                
              const card = document.createElement('div');
              card.className = "bg-[#252a35] rounded-xl p-4 border border-white/5 flex gap-4 items-start hover:border-violet-500/30 transition-colors";
              card.innerHTML = `
                  ${posterImg}
                  <div class="flex flex-col flex-grow h-full">
                      <div class="flex justify-between items-start mb-2">
                           <h3 class="font-black text-white leading-tight text-lg">${escapeHtml(info.title)} <span class="text-gray-500 font-normal text-sm">(${escapeHtml(info.year || "?")})</span></h3>
                           <button type="button" data-fav-remove="${escapeHtml(fav.key)}" data-fav-info="${escapeHtml(encodeData(info))}" class="text-red-500 hover:text-red-400 p-2 ml-2 bg-white/5 rounded-lg transition-colors" title="Eliminar de favoritos">
                               <i class="fas fa-trash-alt"></i>
                           </button>
                      </div>
                      <p class="text-xs text-gray-400 line-clamp-3 mb-3">${escapeHtml(info.overview || "Sin sinopsis disponible.")}</p>
                      
                      <button type="button" data-fav-search="${escapeHtml(info.title)}" class="mt-auto bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white px-4 py-2 rounded-lg text-sm font-bold transition-all w-full flex items-center justify-center gap-2">
                          <i class="fas fa-search"></i> Buscar Torrents
                      </button>
                  </div>
              `;
              container.appendChild(card);
          });
      };

      // Control del Modal de Favoritos
      const favModal = document.getElementById('favoritesModal');
      const favModalInner = document.getElementById('favoritesModalInner');
      
      document.getElementById('openFavoritesBtn').addEventListener('click', () => {
          renderFavorites();
          favModal.classList.remove('hidden');
          // Pequeño delay para animacion
          setTimeout(() => {
              favModal.classList.remove('opacity-0');
              favModalInner.classList.remove('scale-95');
          }, 10);
      });
      
      document.getElementById('closeFavoritesBtn').addEventListener('click', () => {
          favModal.classList.add('opacity-0');
          favModalInner.classList.add('scale-95');
          setTimeout(() => favModal.classList.add('hidden'), 300);
      });
      
      // Cerrar modal clickeando afuera
      favModal.addEventListener('click', (e) => {
          if(e.target === favModal) document.getElementById('closeFavoritesBtn').click();
      });

      // Control del Modal de Subtítulos
      const subModal = document.getElementById('subtitlesModal');
      const subModalInner = document.getElementById('subtitlesModalInner');
      
      window.openSubtitlesModal = async (tmdbId, title) => {
          document.getElementById('subtitlesModalTitle').innerHTML = `<i class="fas fa-closed-captioning text-blue-500"></i> Subtítulos para "${escapeHtml(title)}"`;
          document.getElementById('subtitlesList').innerHTML = '';
          document.getElementById('emptySubtitlesMessage').classList.add('hidden');
          document.getElementById('errorSubtitlesMessage').classList.add('hidden');
          document.getElementById('subtitlesLoading').classList.remove('hidden');
          
          subModal.classList.remove('hidden');
          setTimeout(() => {
              subModal.classList.remove('opacity-0');
              subModalInner.classList.remove('scale-95');
          }, 10);
          
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 15000);
          
          try {
              const res = await fetch(`/api/subtitles/search?tmdb_id=${tmdbId}`, { signal: controller.signal });
              clearTimeout(timeoutId);
              const data = await res.json();
              if(!res.ok) throw new Error(data.error || "Error buscando subtítulos");
              
              document.getElementById('subtitlesLoading').classList.add('hidden');
              
              if(!data.data || data.data.length === 0) {
                  document.getElementById('emptySubtitlesMessage').classList.remove('hidden');
                  return;
              }
              
              let html = '';
              data.data.forEach(sub => {
                  const attrs = sub.attributes;
                  const lang = attrs.language === 'es' ? '🇪🇸 Castellano' : (attrs.language === 'es-mx' || attrs.language === 'es-la' ? '🇲🇽 Latino' : `🗨️ ${attrs.language}`);
                  const fileName = attrs.files[0]?.file_name || 'Subtítulo';
                  const fileId = attrs.files[0]?.file_id;
                  const rating = attrs.ratings || 0;
                  
                  html += `
                      <div class="bg-[#252a35] border border-white/5 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 hover:border-blue-500/30 transition-colors">
                          <div class="flex-grow overflow-hidden">
                              <div class="flex items-center gap-3 mb-2">
                                  <span class="px-2 py-1 bg-gray-800 text-gray-300 rounded text-xs font-bold border border-white/10">${escapeHtml(lang)}</span>
                                  <span class="text-xs text-yellow-500"><i class="fas fa-star"></i> ${escapeHtml(rating)}</span>
                              </div>
                              <p class="text-sm font-bold text-white break-all" title="${escapeHtml(fileName)}">${escapeHtml(fileName)}</p>
                          </div>
                          <button type="button" data-sub-file="${escapeHtml(fileId)}" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 flex-shrink-0">
                              <i class="fas fa-download"></i> Descargar
                          </button>
                      </div>
                  `;
              });
              document.getElementById('subtitlesList').innerHTML = html;
              
          } catch(err) {
              clearTimeout(timeoutId);
              document.getElementById('subtitlesLoading').classList.add('hidden');
              const errorMsg = err.name === 'AbortError' ? "La búsqueda de subtítulos tardó demasiado (Timeout de 15s)." : err.message;
              document.getElementById('errorSubtitlesText').textContent = errorMsg;
              document.getElementById('fallbackSubtitlesLink').href = `https://www.opensubtitles.org/es/search/sublanguageid-spa,spl/imdbid-${tmdbId}`; // Aproximación, la web re-dirige a tmdb a veces, pero ayuda al usuario
              document.getElementById('errorSubtitlesMessage').classList.remove('hidden');
          }
      };
      
      window.downloadSubtitle = async (fileId, btnEl) => {
          const originalText = btnEl.innerHTML;
          btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Obteniendo...';
          btnEl.disabled = true;
          
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 15000);

          try {
              const res = await fetch(`/api/subtitles/download?file_id=${fileId}`, { signal: controller.signal });
              clearTimeout(timeoutId);
              const data = await res.json();
              if(!res.ok) throw new Error(data.error || "Error obteniendo link");
              
              // Abrir en nueva pestaña o iniciar descarga
              window.open(data.link, '_blank');
              setTimeout(() => {
                  btnEl.innerHTML = '<i class="fas fa-check text-green-400"></i> Listo';
                  btnEl.classList.remove("bg-blue-600", "hover:bg-blue-500");
                  btnEl.classList.add("bg-green-600/30", "text-green-400");
              }, 1000);
          } catch(err) {
              clearTimeout(timeoutId);
              const errorMsg = err.name === 'AbortError' ? "La descarga tardó demasiado (Timeout de 15s)." : err.message;
              alert(errorMsg);
              btnEl.innerHTML = originalText;
              btnEl.disabled = false;
          }
      };
      
      document.getElementById('closeSubtitlesBtn').addEventListener('click', () => {
          subModal.classList.add('opacity-0');
          subModalInner.classList.add('scale-95');
          setTimeout(() => subModal.classList.add('hidden'), 300);
      });
      
      // Cerrar modal clickeando afuera
      subModal.addEventListener('click', (e) => {
          if(e.target === subModal) document.getElementById('closeSubtitlesBtn').click();
      });

      visibleMinSize.addEventListener(
        "input",
        (e) => (hiddenMinSize.value = e.target.value),
      );

      filterBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          filterBtns.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          qualityInput.value = btn.getAttribute("data-value");
        });
      });

      // --- Procesamiento de grupos (reutilizado por la paginación server-side) ---
      const getQualityBadge = (title) => {
        const text = title.toLowerCase();
        if (text.includes("remux"))
          return {
            class: "bg-violet-500/10 text-violet-400 border-violet-500/20",
            text: "REMUX",
          };
        if (text.includes("2160p") || text.includes("4k"))
          return {
            class: "bg-blue-500/10 text-blue-400 border-blue-500/20",
            text: "4K UHD",
          };
        if (text.includes("1080p"))
          return {
            class: "bg-green-500/10 text-green-400 border-green-500/20",
            text: "1080p",
          };
        if (text.includes("webrip") || text.includes("web-dl"))
          return {
            class: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
            text: "WEB-DL",
          };
        return {
          class: "bg-gray-500/10 text-gray-400 border-gray-500/20",
          text: "BDRip / Estándar",
        };
      };

      const getSpanishBadge = (supportType) => {
        if (!supportType) return "";
        let colorClass = "bg-orange-500/10 text-orange-400 border-orange-500/20";
        let icon = '<i class="fas fa-comment-dots mr-1"></i>';
        if (supportType === "Latino" || supportType === "Castellano") {
          colorClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
          icon = '<i class="fas fa-language mr-1"></i>';
        }
        return `<span class="px-2 py-1 flex-shrink-0 ${colorClass} text-[10px] font-bold rounded border lowercase inline-flex items-center" title="Soporte detectado en el título">${icon}${escapeHtml(supportType)}</span>`;
      };

      const buildValidGroups = (rawResults) => {
        const isLatino = document.getElementById("langLatino").checked;
        const isCastellano = document.getElementById("langCastellano").checked;
        const isSub = document.getElementById("langSub").checked;
        const isOtro = document.getElementById("langOtro").checked;
        const noLanguageFilterApplied = !isLatino && !isCastellano && !isSub && !isOtro;

        const validGroups = [];

        (rawResults || []).forEach((group) => {
          const info = group.group_info;

          let torrentsHTML = "";
          let visibleCount = 0;
          group.torrents.forEach((t) => {
            const support = t.spanish_support;
            let show = false;

            if (noLanguageFilterApplied) {
              show = true;
            } else {
              if (support === "Latino" && isLatino) show = true;
              else if (support === "Castellano" && isCastellano) show = true;
              else if (support === "Subtitulado" && isSub) show = true;
              else if (!support && isOtro) show = true;
            }

            if (!show) return;
            visibleCount++;
            const badge = getQualityBadge(t.title);
            // escapeHtml cubre también el atributo: ningún metadato externo entra crudo
            const safeMagnet = escapeHtml(t.magnet || "");

            const copyBtnHTML = t.magnet
              ? `<button type="button" data-magnet-copy="${safeMagnet}" class="text-gray-400 hover:text-white transition-colors p-3 rounded-lg bg-white/5 hover:bg-violet-600/50" title="Copiar Magnet">
                                <i class="fas fa-copy"></i>
                            </button>`
              : "";

            const delugeBtnHTML = t.magnet
              ? `<button type="button" data-magnet-deluge="${safeMagnet}" class="bg-violet-600 hover:bg-violet-500 text-white px-4 py-3 rounded-lg text-sm font-bold flex items-center gap-2 transition-all flex-grow md:flex-grow-0 justify-center group/deluge">
                                <i class="fas fa-cloud-download-alt"></i> <span class="btn-text">Enviar a Deluge</span>
                            </button>`
              : `<span class="text-xs text-gray-500">Sin link</span>`;

            const fullSeasonBadge = t.is_full_season
              ? `<span class="px-2 py-1 bg-amber-500/20 text-amber-400 border-amber-500/30 flex-shrink-0 text-[10px] uppercase font-black rounded border"><i class="fas fa-star mr-1"></i>Temporada Completa</span>`
              : "";

            torrentsHTML += `
                            <div class="bg-[#252a35] rounded-xl p-4 mb-3 border border-white/5 flex flex-col xl:flex-row gap-4 xl:items-center justify-between hover:border-violet-500/30 transition-colors">
                                <div class="flex-grow w-full overflow-hidden">
                                    <div class="flex flex-wrap items-center gap-2 mb-2">
                                        ${fullSeasonBadge}
                                        <span class="px-2 py-1 ${badge.class} flex-shrink-0 text-[10px] font-bold rounded border">${badge.text}</span>
                                        ${t.quality !== "Desconocida" ? `<span class="px-2 py-1 bg-gray-700 flex-shrink-0 text-gray-300 text-[10px] rounded">${escapeHtml(t.quality)}</span>` : ""}
                                        ${t.codec ? `<span class="px-2 py-1 bg-gray-700 text-gray-300 flex-shrink-0 text-[10px] rounded">${escapeHtml(t.codec)}</span>` : ""}
                                        ${getSpanishBadge(t.spanish_support)}
                                        ${t.audio_support ? `<span class="px-2 py-1 bg-cyan-500/10 text-cyan-400 border-cyan-500/20 flex-shrink-0 text-[10px] font-bold rounded border inline-flex items-center" title="Formato de audio detectado"><i class="fas fa-volume-up mr-1" aria-hidden="true"></i>${escapeHtml(t.audio_support)}</span>` : ""}
                                        <span class="text-blue-400 font-bold ml-auto flex-shrink-0">${escapeHtml(t.size_gb)} GB</span>
                                    </div>
                                    <p class="text-sm text-gray-400 mb-2 truncate" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</p>
                                    <div class="flex items-center gap-3 text-xs text-gray-500">
                                        <span><i class="fas fa-arrow-up text-green-500 mr-1"></i> ${escapeHtml(t.seeders)}</span>
                                        <span class="truncate"><i class="fas fa-server mr-1"></i> ${escapeHtml(t.tracker)}</span>
                                    </div>
                                </div>
                                <div class="flex items-center w-full xl:w-auto gap-2 mt-2 xl:mt-0">
                                    ${copyBtnHTML}
                                    ${delugeBtnHTML}
                                </div>
                            </div>
                        `;
          });

          if (visibleCount > 0) {
            validGroups.push({
              info: info,
              visibleTorrentsHTML: torrentsHTML,
              visibleCount: visibleCount,
              groupKey: `fav_${info.title.replace(/\s+/g, "_")}_${info.year}`,
            });
          }
        });

        return validGroups;
      };

      document
        .getElementById("searchForm")
        .addEventListener("submit", async (e) => {
          e.preventDefault();

          // Cancela cualquier búsqueda anterior en curso antes de lanzar la nueva
          const mySequence = ++searchSequence;
          if (activeSearchController) activeSearchController.abort();
          activeSearchController = new AbortController();
          const searchSignal = activeSearchController.signal;
          showGlobalLoader();

          const query = document.getElementById("query").value;
          const minSize = hiddenMinSize.value;
          const qualityTag = qualityInput.value;
          const category =
            document.querySelector('input[name="category"]:checked')?.value ||
            "all";
          const requireHdr = document.getElementById("filterHDR").checked;
          const requireHevc = document.getElementById("filterHEVC").checked;

          const btnText = document.getElementById("btnText");
          const btnSpinner = document.getElementById("btnSpinner");
          const searchBtn = document.getElementById("searchBtn");
          const resultsSection = document.getElementById("resultsSection");
          const resultsList = document.getElementById("resultsList");
          const resultsCount = document.getElementById("resultsCount");
          const errorBox = document.getElementById("errorBox");
          const errorMessage = document.getElementById("errorMessage");

          searchBtn.disabled = true;
          searchBtn.classList.add("opacity-75", "cursor-not-allowed");
          btnText.textContent = "Buscando...";
          btnSpinner.classList.remove("hidden");

          resultsSection.classList.add("hidden");
          errorBox.classList.add("hidden");
          resultsList.innerHTML = "";
          document.getElementById('loadMoreContainer').classList.add('hidden');
          
          // INIT VARS
          globalCurrentResults = [];
          globalRenderedCount = 0;
          globalPage = 1;
          globalHasMore = false;
          globalTotalGroups = 0;
          globalSearchParams = null;

          // Función con reintentos para lidiar con el Timeout de Cloudflare (504 o 502) en Jackett
          const fetchWithRetry = async (url, retries = 2) => {
              for (let i = 0; i <= retries; i++) {
                  try {
                      btnText.textContent = i > 0 ? `Reintentando (${i}/${retries})...` : "Buscando...";
                      const response = await fetch(url, { signal: searchSignal });
                      const data = await response.json();
                      if (!response.ok) {
                          if ((response.status === 504 || response.status === 502) && i < retries) {
                              console.warn(`Intento ${i+1} fallido por Timeout. Reintentando...`);
                              continue;
                          }
                          throw new Error(data.error || "Ocurrió un error en el servidor backend.");
                      }
                      return data;
                  } catch (error) {
                      if (error.name === "AbortError") throw error;
                      if (i === retries) throw error;
                  }
              }
          };

          try {
            const isLatino = document.getElementById("langLatino").checked;
            const isCastellano = document.getElementById("langCastellano").checked;
            const isSub = document.getElementById("langSub").checked;
            const isOtro = document.getElementById("langOtro").checked;

            const selectedLangs = [];
            if (isLatino) selectedLangs.push("latino");
            if (isCastellano) selectedLangs.push("castellano");
            if (isSub) selectedLangs.push("sub");
            if (isOtro) selectedLangs.push("otros");

            const langFilterVal = selectedLangs.length > 0 ? selectedLangs.join(",") : "all";

            const params = new URLSearchParams({
              query: query,
              min_size_gb: minSize,
              quality_tag: qualityTag,
              category: category,
              hdr: requireHdr,
              hevc: requireHevc,
              lang_filter: langFilterVal,
              page: 1,
              per_page: RESULTS_PER_PAGE,
            });

            const data = await fetchWithRetry(`/api/search?${params.toString()}`);

            // Guardar datos crudos para la exportación
            globalRawResults = data.results;
            globalLastQuery = query;

            if (data.results.length === 0) {
              throw new Error(
                "No se encontraron resultados que superen los filtros de tamaño o calidad para esta búsqueda.",
              );
            }

            const validGroups = buildValidGroups(data.results);

            if (validGroups.length === 0) {
              throw new Error(
                "No se encontraron resultados tras aplicar los filtros locales de idioma (Intenta habilitar Otros, Latino, etc).",
              );
            }

            // Estado de paginación server-side
            globalPage = data.page || 1;
            globalHasMore = Boolean(data.has_more);
            globalTotalGroups =
              typeof data.total_groups === "number"
                ? data.total_groups
                : validGroups.length;
            globalSearchParams = params;

            globalCurrentResults = validGroups;
            globalRenderedCount = 0;
            resultsList.innerHTML = "";

            resultsCount.textContent = `${globalTotalGroups} OBRA${globalTotalGroups !== 1 ? "S" : ""} ENCONTRADA${globalTotalGroups !== 1 ? "S" : ""}`;
            resultsSection.classList.remove("hidden");

            renderNextBatch();
          } catch (error) {
            // Ignora errores de búsquedas canceladas o reemplazadas por una más reciente
            if (error.name === "AbortError" || mySequence !== searchSequence) return;
            errorMessage.textContent = error.message;
            errorBox.classList.remove("hidden");
          } finally {
            // Solo la búsqueda más reciente puede restaurar la UI
            if (mySequence === searchSequence) {
              searchBtn.disabled = false;
              searchBtn.classList.remove("opacity-75", "cursor-not-allowed");
              btnText.textContent = "Buscar";
              btnSpinner.classList.add("hidden");
              hideGlobalLoader();
            }
          }
        });
        
        // FUNCIÓN DE RENDERIZADO POR LOTES (LAZY LOADING MANUAL)
        function renderNextBatch() {
            const fragment = document.createDocumentFragment();
            const resultsList = document.getElementById("resultsList");
            const loadMoreContainer = document.getElementById('loadMoreContainer');
            
            const nextBatch = globalCurrentResults.slice(globalRenderedCount, globalRenderedCount + RESULTS_PER_PAGE);
            
            nextBatch.forEach((groupObj) => {
               const { info, visibleTorrentsHTML, visibleCount, groupKey } = groupObj;
               
               const posterImg = info.poster_url
                ? `<img src="${escapeHtml(info.poster_url)}" alt="${escapeHtml(info.title)}" class="w-full h-[400px] object-cover object-top border-b border-white/10" loading="lazy">`
                : `<div class="w-full h-[400px] bg-gradient-to-b from-gray-800 to-[#1a1d24] flex items-center justify-center border-b border-white/10">
                               <i class="fas fa-film text-6xl text-gray-600"></i>
                           </div>`;

              const card = document.createElement("div");
              card.className = `movie-group-card group bg-[#1a1d24] border border-white/10 rounded-2xl overflow-hidden flex flex-col`;

              const isFav = favorites.some(f => f.key === groupKey);
              const favIcon = isFav ? '<i class="fas fa-heart"></i>' : '<i class="far fa-heart"></i>';
              const favClass = isFav ? 'text-red-500' : 'text-gray-400';

              card.innerHTML = `
                        <div class="relative group/poster">
                            ${posterImg}
                            <div class="absolute inset-0 bg-black/60 opacity-0 group-hover/poster:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-sm">
                                <button type="button" class="fav-btn ${favClass} bg-white/10 hover:bg-white/20 p-4 rounded-full text-3xl transition-all transform hover:scale-110 shadow-2xl" data-key="${escapeHtml(groupKey)}" data-fav-info="${escapeHtml(encodeData(info))}" title="Guardar / Quitar Favorito">
                                    ${favIcon}
                                </button>
                            </div>
                        </div>
                        <div class="p-6 flex flex-col flex-grow">
                            <h3 class="text-2xl font-black text-white mb-2 leading-tight">${escapeHtml(info.title)} <span class="text-gray-500 font-normal">(${escapeHtml(info.year || "?")})</span></h3>
                            <p class="text-sm text-gray-400 mb-6 line-clamp-3" title="${escapeHtml(info.overview || "")}">${escapeHtml(info.overview || "Sin sinopsis disponible.")}</p>
                            
                            <div class="flex gap-2 mt-auto mb-4">
                                <button type="button" data-sub-id="${escapeHtml(info.id)}" data-sub-title="${escapeHtml(info.title)}" class="bg-blue-600/10 border border-blue-500/20 hover:bg-blue-600 text-blue-400 hover:text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2">
                                    <i class="fas fa-closed-captioning"></i> Buscar Subtítulos
                                </button>
                            </div>

                            <details class="group/details">
                                <summary class="list-none cursor-pointer bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-4 font-bold text-center transition-colors flex items-center justify-center gap-2">
                                    <span class="text-violet-400">Ver ${visibleCount} Torrents Disponibles</span>
                                    <i class="fas fa-chevron-down group-open/details:rotate-180 transition-transform text-white"></i>
                                </summary>
                                <div class="mt-4 pt-4 border-t border-white/5">
                                    ${visibleTorrentsHTML}
                                </div>
                            </details>
                        </div>
                    `;
              fragment.appendChild(card);
            });
            
            resultsList.appendChild(fragment);
            globalRenderedCount += nextBatch.length;
            
            // La visibilidad la controla el servidor (has_more), no el conteo local
            if (globalHasMore) {
                loadMoreContainer.classList.remove('hidden');
            } else {
                loadMoreContainer.classList.add('hidden');
            }
        }
        
        // Carga de la siguiente página desde el servidor
        document.getElementById('loadMoreBtn').addEventListener('click', async () => {
            if (!globalHasMore || globalLoadingMore || !globalSearchParams) return;

            globalLoadingMore = true;
            const btn = document.getElementById('loadMoreBtn');
            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.classList.add('opacity-75', 'cursor-not-allowed');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Cargando más...';

            try {
                const nextPage = (globalPage || 1) + 1;
                const params = new URLSearchParams(globalSearchParams);
                params.set('page', nextPage);

                const response = await fetch(`/api/search?${params.toString()}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Error cargando más resultados.');
                }

                const newGroups = buildValidGroups(data.results || []);

                // Acumular resultados para renderizado y exportación
                globalCurrentResults = globalCurrentResults.concat(newGroups);
                globalRawResults = (globalRawResults || []).concat(data.results || []);
                globalPage = data.page || nextPage;
                globalHasMore = Boolean(data.has_more);
                if (typeof data.total_groups === 'number') {
                    globalTotalGroups = data.total_groups;
                }

                // Posicionar el cursor de renderizado al inicio del nuevo lote
                globalRenderedCount = globalCurrentResults.length - newGroups.length;
                renderNextBatch();
            } catch (error) {
                alert(error.message);
            } finally {
                btn.disabled = false;
                btn.classList.remove('opacity-75', 'cursor-not-allowed');
                btn.innerHTML = originalHTML;
                globalLoadingMore = false;
            }
        });

        // Función RPC Enviar a Deluge Remoto
        async function sendToDeluge(magnetUrl, btnElement) {
            const originalHTML = btnElement.innerHTML;
            const originalClasses = btnElement.className;
            const textSpan = btnElement.querySelector('.btn-text');
            const icon = btnElement.querySelector('i');
            
            icon.className = 'fas fa-spinner fa-spin';
            textSpan.textContent = 'Enviando...';
            btnElement.disabled = true;
            btnElement.classList.add('opacity-75', 'cursor-not-allowed');

            try {
                const res = await fetch('/api/deluge/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ magnet: magnetUrl })
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || 'Ocurrió un error de red o de clave incorrecta.');
                }

                // Éxito: Pintar botón de Verde temporalmente
                btnElement.innerHTML = '<i class="fas fa-check"></i> <span class="btn-text">Añadido!</span>';
                btnElement.className = 'bg-emerald-500 text-white px-4 py-3 rounded-lg text-sm font-bold flex items-center gap-2 transition-all flex-grow md:flex-grow-0 justify-center';
                
                setTimeout(() => {
                    btnElement.innerHTML = originalHTML;
                    btnElement.className = originalClasses;
                    btnElement.disabled = false;
                    btnElement.classList.remove('opacity-75', 'cursor-not-allowed');
                }, 4000);

            } catch (error) {
                alert("Error interactuando con Deluge:\n" + error.message);
                btnElement.innerHTML = originalHTML;
                btnElement.disabled = false;
                btnElement.classList.remove('opacity-75', 'cursor-not-allowed');
            }
        }

        // --- Delegación de eventos ---
        // Toda acción que depende de datos externos se resuelve por atributos data-*,
        // nunca interpolando código dentro de un atributo onclick.
        document.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('[data-magnet-copy]');
    if (copyBtn) {
        const magnet = copyBtn.getAttribute('data-magnet-copy');
        navigator.clipboard.writeText(magnet).then(() => alert('¡Enlace Magnet copiado!'));
        return;
    }
    
    const delugeBtn = e.target.closest('[data-magnet-deluge]');
    if (delugeBtn) {
        const magnet = delugeBtn.getAttribute('data-magnet-deluge');
        sendToDeluge(magnet, delugeBtn);
        return;
    }

    // Favorito desde la tarjeta de resultados
    const favBtn = e.target.closest('.fav-btn');
    if (favBtn) {
        const rawInfo = favBtn.getAttribute('data-fav-info');
        if (!rawInfo) return;
        try {
            toggleFavorite(favBtn.getAttribute('data-key'), JSON.parse(decodeURIComponent(rawInfo)));
        } catch (err) {
            console.warn('No se pudo actualizar el favorito:', err);
        }
        return;
    }

    // Quitar favorito desde el modal de favoritos
    const favRemove = e.target.closest('[data-fav-remove]');
    if (favRemove) {
        const rawInfo = favRemove.getAttribute('data-fav-info');
        if (!rawInfo) return;
        try {
            toggleFavorite(favRemove.getAttribute('data-fav-remove'), JSON.parse(decodeURIComponent(rawInfo)));
        } catch (err) {
            console.warn('No se pudo eliminar el favorito:', err);
        }
        return;
    }

    // Buscar torrents desde una tarjeta de favoritos
    const favSearch = e.target.closest('[data-fav-search]');
    if (favSearch) {
        document.getElementById('query').value = favSearch.getAttribute('data-fav-search');
        document.getElementById('closeFavoritesBtn').click();
        document.getElementById('searchBtn').click();
        return;
    }

    // Abrir modal de subtítulos
    const subBtn = e.target.closest('[data-sub-id]');
    if (subBtn) {
        window.openSubtitlesModal(subBtn.getAttribute('data-sub-id'), subBtn.getAttribute('data-sub-title'));
        return;
    }

    // Descargar subtítulo
    const subDownload = e.target.closest('[data-sub-file]');
    if (subDownload) {
        window.downloadSubtitle(subDownload.getAttribute('data-sub-file'), subDownload);
    }
});

// --- Búsqueda en tiempo real con debounce ---
// Espera 1200ms tras la última pulsación, exige al menos 4 caracteres
// y evita repetir la misma búsqueda. Las búsquedas previas se cancelan
// automáticamente gracias al AbortController del handler de "submit".
let realtimeSearchTimer = null;
let lastRealtimeQuery = "";
const realtimeQueryInput = document.getElementById("query");

realtimeQueryInput.addEventListener("input", () => {
    clearTimeout(realtimeSearchTimer);
    const value = realtimeQueryInput.value.trim();

    // No buscar con términos demasiado cortos
    if (value.length < 4) {
        lastRealtimeQuery = "";
        return;
    }

    realtimeSearchTimer = setTimeout(() => {
        if (value === lastRealtimeQuery) return;
        lastRealtimeQuery = value;
        document.getElementById("searchForm").requestSubmit();
    }, 1200);
});

// --- Exportación de resultados (JSON / CSV) ---
const downloadBlob = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};

const csvEscape = (value) => {
    const text = value === null || value === undefined ? "" : String(value);
    return `"${text.replace(/"/g, '""')}"`;
};

const buildExportSlug = () => {
    const slug = (globalLastQuery || "resultados")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/gi, "_")
        .replace(/^_+|_+$/g, "")
        .toLowerCase();
    return slug || "resultados";
};

const exportResults = (format) => {
    if (!globalRawResults || globalRawResults.length === 0) {
        alert("No hay resultados para exportar. Realiza una búsqueda primero.");
        return;
    }

    const slug = buildExportSlug();
    const date = new Date().toISOString().slice(0, 10);
    const baseName = `media-tracker_${slug}_${date}`;

    if (format === "json") {
        const payload = globalRawResults.map((group) => ({
            title: group.group_info?.title,
            year: group.group_info?.year,
            tmdb_id: group.group_info?.id,
            overview: group.group_info?.overview,
            poster_url: group.group_info?.poster_url,
            torrents: (group.torrents || []).map((t) => ({
                title: t.title,
                size_gb: t.size_gb,
                seeders: t.seeders,
                tracker: t.tracker,
                quality: t.quality,
                codec: t.codec,
                spanish_support: t.spanish_support,
                audio_support: t.audio_support,
                is_full_season: t.is_full_season,
                season: t.season,
                episode: t.episode,
                magnet: t.magnet,
            })),
        }));
        downloadBlob(
            JSON.stringify(payload, null, 2),
            `${baseName}.json`,
            "application/json;charset=utf-8"
        );
        return;
    }

    // CSV
    const headers = [
        "Obra",
        "Año",
        "Título del torrent",
        "Tamaño (GB)",
        "Seeders",
        "Tracker",
        "Calidad",
        "Codec",
        "Idioma",
        "Audio",
        "Temporada completa",
        "Magnet",
    ];
    const rows = [headers.map(csvEscape).join(",")];

    globalRawResults.forEach((group) => {
        (group.torrents || []).forEach((t) => {
            rows.push(
                [
                    group.group_info?.title,
                    group.group_info?.year,
                    t.title,
                    t.size_gb,
                    t.seeders,
                    t.tracker,
                    t.quality,
                    t.codec,
                    t.spanish_support || "",
                    t.audio_support || "",
                    t.is_full_season ? "Sí" : "No",
                    t.magnet || "",
                ]
                    .map(csvEscape)
                    .join(",")
            );
        });
    });

    // BOM UTF-8 para que Excel reconozca los acentos
    downloadBlob(
        "\uFEFF" + rows.join("\r\n"),
        `${baseName}.csv`,
        "text/csv;charset=utf-8"
    );
};

document.getElementById("exportJsonBtn")?.addEventListener("click", () => exportResults("json"));
document.getElementById("exportCsvBtn")?.addEventListener("click", () => exportResults("csv"));
