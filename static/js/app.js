const filterBtns = document.querySelectorAll(".filter-btn");
      const qualityInput = document.getElementById("quality_tag");
      const visibleMinSize = document.getElementById("visible_min_size");
      const hiddenMinSize = document.getElementById("min_size_gb");
      
      // ESTADO GLOBAL
      let globalCurrentResults = [];
      let globalRenderedCount = 0;
      const RESULTS_PER_PAGE = 16;
      let favorites = JSON.parse(localStorage.getItem('mt_favorites')) || [];

      // Funciones de Favoritos
      const saveFavorites = () => localStorage.setItem('mt_favorites', JSON.stringify(favorites));
      
      const toggleFavorite = (groupKey, groupInfoStr) => {
          const groupInfo = JSON.parse(decodeURIComponent(groupInfoStr));
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
          const btn = document.querySelector(`.fav-btn[data-key="${groupKey}"]`);
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
                ? `<img src="${info.poster_url}" alt="${info.title}" class="w-24 h-36 object-cover rounded-lg shadow-md flex-shrink-0">`
                : `<div class="w-24 h-36 bg-gray-800 rounded-lg shadow-md flex-shrink-0 flex items-center justify-center"><i class="fas fa-film text-3xl text-gray-600"></i></div>`;
                
              const card = document.createElement('div');
              card.className = "bg-[#252a35] rounded-xl p-4 border border-white/5 flex gap-4 items-start hover:border-violet-500/30 transition-colors";
              card.innerHTML = `
                  ${posterImg}
                  <div class="flex flex-col flex-grow h-full">
                      <div class="flex justify-between items-start mb-2">
                           <h3 class="font-black text-white leading-tight text-lg">${info.title} <span class="text-gray-500 font-normal text-sm">(${info.year || "?"})</span></h3>
                           <button onclick="toggleFavorite('${fav.key}', '${encodeURIComponent(JSON.stringify(info))}')" class="text-red-500 hover:text-red-400 p-2 ml-2 bg-white/5 rounded-lg transition-colors" title="Eliminar de favoritos">
                               <i class="fas fa-trash-alt"></i>
                           </button>
                      </div>
                      <p class="text-xs text-gray-400 line-clamp-3 mb-3">${info.overview}</p>
                      
                      <button onclick="document.getElementById('query').value='${info.title}'; document.getElementById('closeFavoritesBtn').click(); document.getElementById('searchBtn').click();" class="mt-auto bg-violet-600/20 hover:bg-violet-600 text-violet-300 hover:text-white px-4 py-2 rounded-lg text-sm font-bold transition-all w-full flex items-center justify-center gap-2">
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
          document.getElementById('subtitlesModalTitle').innerHTML = `<i class="fas fa-closed-captioning text-blue-500"></i> Subtítulos para "${title}"`;
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
                                  <span class="px-2 py-1 bg-gray-800 text-gray-300 rounded text-xs font-bold border border-white/10">${lang}</span>
                                  <span class="text-xs text-yellow-500"><i class="fas fa-star"></i> ${rating}</span>
                              </div>
                              <p class="text-sm font-bold text-white break-all" title="${fileName}">${fileName}</p>
                          </div>
                          <button onclick="downloadSubtitle(${fileId}, this)" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 flex-shrink-0">
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

      document
        .getElementById("searchForm")
        .addEventListener("submit", async (e) => {
          e.preventDefault();

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

          // Función con reintentos para lidiar con el Timeout de Cloudflare (504 o 502) en Jackett
          const fetchWithRetry = async (url, retries = 2) => {
              for (let i = 0; i <= retries; i++) {
                  try {
                      btnText.textContent = i > 0 ? `Reintentando (${i}/${retries})...` : "Buscando...";
                      const response = await fetch(url);
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
            });

            const data = await fetchWithRetry(`/api/search?${params.toString()}`);

            if (data.results.length === 0) {
              throw new Error(
                "No se encontraron resultados que superen los filtros de tamaño o calidad para esta búsqueda.",
              );
            }

            let validGroups = [];

            const getQualityBadge = (title) => {
              const text = title.toLowerCase();
              if (text.includes("remux"))
                return {
                  class:
                    "bg-violet-500/10 text-violet-400 border-violet-500/20",
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
                  class:
                    "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
                  text: "WEB-DL",
                };
              return {
                class: "bg-gray-500/10 text-gray-400 border-gray-500/20",
                text: "BDRip / Estándar",
              };
            };

            const getSpanishBadge = (supportType) => {
              if (!supportType) return "";
              let colorClass =
                "bg-orange-500/10 text-orange-400 border-orange-500/20";
              let icon = '<i class="fas fa-comment-dots mr-1"></i>';

              if (supportType === "Latino" || supportType === "Castellano") {
                colorClass =
                  "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                icon = '<i class="fas fa-language mr-1"></i>';
              }

              return `<span class="px-2 py-1 flex-shrink-0 ${colorClass} text-[10px] font-bold rounded border lowercase inline-flex items-center" title="Soporte detectado en el título">${icon}${supportType}</span>`;
            };

            // Variables ya declaradas al inicio de la función de búsqueda
            
            const noLanguageFilterApplied = !isLatino && !isCastellano && !isSub && !isOtro;

            // data.results = [{"group_info": {...}, "torrents": [...]}]
            data.results.forEach((group) => {
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
                const safeMagnet = t.magnet ? t.magnet.replace(/"/g, '&quot;') : "";

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
                                        ${t.quality !== "Desconocida" ? `<span class="px-2 py-1 bg-gray-700 flex-shrink-0 text-gray-300 text-[10px] rounded">${t.quality}</span>` : ""}
                                        ${t.codec ? `<span class="px-2 py-1 bg-gray-700 text-gray-300 flex-shrink-0 text-[10px] rounded">${t.codec}</span>` : ""}
                                        ${getSpanishBadge(t.spanish_support)}
                                        ${t.audio_support ? `<span class="px-2 py-1 bg-cyan-500/10 text-cyan-400 border-cyan-500/20 flex-shrink-0 text-[10px] font-bold rounded border inline-flex items-center" title="Formato de audio detectado"><i class="fas fa-volume-up mr-1" aria-hidden="true"></i>${t.audio_support}</span>` : ""}
                                        <span class="text-blue-400 font-bold ml-auto flex-shrink-0">${t.size_gb} GB</span>
                                    </div>
                                    <p class="text-sm text-gray-400 mb-2 truncate" title="${t.title}">${t.title}</p>
                                    <div class="flex items-center gap-3 text-xs text-gray-500">
                                        <span><i class="fas fa-arrow-up text-green-500 mr-1"></i> ${t.seeders}</span>
                                        <span class="truncate"><i class="fas fa-server mr-1"></i> ${t.tracker}</span>
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
                     groupKey: `fav_${info.title.replace(/\s+/g,'_')}_${info.year}`
                 });
              }
            });

            if (validGroups.length === 0) {
              throw new Error(
                "No se encontraron resultados tras aplicar los filtros locales de idioma (Intenta habilitar Otros, Latino, etc).",
              );
            }

            globalCurrentResults = validGroups;
            globalRenderedCount = 0;
            resultsList.innerHTML = '';
            
            resultsCount.textContent = `${validGroups.length} OBRA${validGroups.length !== 1 ? 'S' : ''} ENCONTRADA${validGroups.length !== 1 ? 'S' : ''}`;
            resultsSection.classList.remove("hidden");
            
            renderNextBatch();
          } catch (error) {
            errorMessage.textContent = error.message;
            errorBox.classList.remove("hidden");
          } finally {
            searchBtn.disabled = false;
            searchBtn.classList.remove("opacity-75", "cursor-not-allowed");
            btnText.textContent = "Buscar";
            btnSpinner.classList.add("hidden");
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
                ? `<img src="${info.poster_url}" alt="${info.title}" class="w-full h-[400px] object-cover object-top border-b border-white/10" loading="lazy">`
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
                                <button type="button" class="fav-btn ${favClass} bg-white/10 hover:bg-white/20 p-4 rounded-full text-3xl transition-all transform hover:scale-110 shadow-2xl" data-key="${groupKey}" onclick="toggleFavorite('${groupKey}', '${encodeURIComponent(JSON.stringify(info))}')" title="Guardar / Quitar Favorito">
                                    ${favIcon}
                                </button>
                            </div>
                        </div>
                        <div class="p-6 flex flex-col flex-grow">
                            <h3 class="text-2xl font-black text-white mb-2 leading-tight">${info.title} <span class="text-gray-500 font-normal">(${info.year || "?"})</span></h3>
                            <p class="text-sm text-gray-400 mb-6 line-clamp-3" title="${info.overview}">${info.overview}</p>
                            
                            <div class="flex gap-2 mt-auto mb-4">
                                <button type="button" onclick="openSubtitlesModal('${info.id}', '${info.title.replace(/'/g, "\\'")}')" class="bg-blue-600/10 border border-blue-500/20 hover:bg-blue-600 text-blue-400 hover:text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2">
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
            
            if (globalRenderedCount >= globalCurrentResults.length) {
                loadMoreContainer.classList.add('hidden');
            } else {
                loadMoreContainer.classList.remove('hidden');
            }
        }
        
        document.getElementById('loadMoreBtn').addEventListener('click', renderNextBatch);

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
        }document.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('[data-magnet-copy]');
    if (copyBtn) {
        const magnet = copyBtn.getAttribute('data-magnet-copy');
        navigator.clipboard.writeText(magnet).then(() => alert('¡Enlace Magnet copiado!'));
    }
    
    const delugeBtn = e.target.closest('[data-magnet-deluge]');
    if (delugeBtn) {
        const magnet = delugeBtn.getAttribute('data-magnet-deluge');
        sendToDeluge(magnet, delugeBtn);
    }
});
