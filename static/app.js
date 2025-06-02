;(function(){
  // --- Element refs ---
  const inp        = document.getElementById("input");
  const prev       = document.getElementById("preview");
  const hist       = document.getElementById("history");
  const btnPreview = document.getElementById("btn-preview");
  const btnDocx    = document.getElementById("btn-docx");
  const btnClear   = document.getElementById("btn-clear");
  const spinner    = document.getElementById("spinner");

  // Check if elements were found
  if (!inp) console.error("[app.js] Element with ID 'input' not found!");
  if (!prev) console.error("[app.js] Element with ID 'preview' not found!");
  if (!hist) console.error("[app.js] Element with ID 'history' not found!");
  if (!btnPreview) console.error("[app.js] Element with ID 'btn-preview' not found!");
  if (!btnDocx) console.error("[app.js] Element with ID 'btn-docx' not found!");
  if (!btnClear) console.error("[app.js] Element with ID 'btn-clear' not found!");
  if (!spinner) console.error("[app.js] Element with ID 'spinner' not found!");


  // --- Load & save history from localStorage ---
  let history = JSON.parse(localStorage.getItem("farsiFixerHistory") || "[]");

  // Track object URLs to revoke them when no longer needed
  const objectUrls = new Set();

  function saveHistory(){
    localStorage.setItem("farsiFixerHistory", JSON.stringify(history));
  }

  // --- Render the History sidebar ---
  function renderHistory(){
    if (!hist) {
        console.error("[app.js] History element not found, cannot render history.");
        return;
    }
    hist.innerHTML = "";

    if (history.length === 0) {
      const emptyMsg = document.createElement("div");
      emptyMsg.className = "text-gray-500 text-center py-4";
      emptyMsg.textContent = "تاریخچه خالی است";
      hist.appendChild(emptyMsg);
      if (btnClear) btnClear.style.display = "none";
      return;
    }

    history.slice().reverse().forEach(entry => {
      const li   = document.createElement("li"),
            info = document.createElement("div"),
            btns = document.createElement("div"),
            docx = document.createElement("a");

      info.innerHTML = `
        <div class="font-medium">${entry.time}</div>
        <div class="text-sm text-gray-600 truncate">${entry.snip}…</div>
      `;
      info.className = "flex-1 min-w-0";

      if (entry.docx) {
        docx.textContent  = "DOCX";
        docx.href         = entry.docx;
        docx.download     = `FarsiText_${entry.time.replace(/[\s:]/g, '_')}.docx`;
        docx.className    = "history-btn px-2 py-1 bg-purple-600 text-white rounded";
        // objectUrls.add(entry.docx); // Object URLs are added when created in convert() or btnDocx.onclick
                                     // No need to re-add here, but ensure it's managed correctly.
                                     // It's already added when the blob URL is created.
        btns.append(docx);
      }

      btns.className = "flex flex-col gap-2";
      li.className = "flex justify-between items-start";
      li.append(info, btns);
      hist.append(li);
    });

    if (btnClear) btnClear.style.display = "block";
  }

  // --- Clear history handler ---
  if (btnClear) {
    btnClear.onclick = () => {
      console.log("[app.js] btnClear clicked");
      objectUrls.forEach(url => {
        console.log("[app.js] Revoking URL from history clear:", url);
        URL.revokeObjectURL(url);
      });
      objectUrls.clear();
      history = [];
      saveHistory();
      renderHistory();
    };
  }


  // --- Preview handler (debounced) ---
  let previewTimer;
  if (inp) {
    inp.oninput = () => {
      clearTimeout(previewTimer);
      previewTimer = setTimeout(()=> {
        if (!inp.value.trim()) {
          if (prev) prev.innerHTML = '<div class="text-gray-400 italic">پیش‌نمایش در اینجا نمایش داده می‌شود...</div>';
          return;
        }
        try {
          if (prev && typeof marked !== 'undefined') prev.innerHTML = marked.parse(inp.value);
          else if (prev) prev.innerHTML = '<div class="text-red-500">Marked.js not loaded.</div>';
        } catch (err) {
          if (prev) prev.innerHTML = `<div class="text-red-500">خطا در پردازش: ${err.message}</div>`;
        }
      }, 300);
    };
  }

  if (btnPreview) {
    btnPreview.onclick = () => {
      console.log("[app.js] btnPreview clicked");
      clearTimeout(previewTimer);
      if (!inp || !inp.value.trim()) {
        if (prev) prev.innerHTML = '<div class="text-gray-400 italic">متن خالی است</div>';
        return;
      }
      try {
        if (prev && typeof marked !== 'undefined') prev.innerHTML = marked.parse(inp.value);
        else if (prev) prev.innerHTML = '<div class="text-red-500">Marked.js not loaded.</div>';
      } catch (err) {
        if (prev) prev.innerHTML = `<div class="text-red-500">خطا در پردازش: ${err.message}</div>`;
      }
    };
  }


  // --- Toggle loading state ---
  function setLoading(isLoading) {
    const buttons = [];
    if (btnPreview) buttons.push(btnPreview);
    if (btnDocx) buttons.push(btnDocx);

    const validButtons = buttons.filter(b => b !== null);

    if (isLoading) {
      validButtons.forEach(b => { b.disabled = true; });
      if (spinner) spinner.style.display = "flex";
    } else {
      validButtons.forEach(b => { b.disabled = false; });
      if (spinner) spinner.style.display = "none";
    }
  }

  // --- Conversion call ---
  async function convert(fmt) {
    if (!inp || !inp.value.trim()) {
      alert("لطفاً متنی را وارد کنید");
      return null;
    }

    const form = new FormData();
    form.append("text", inp.value);
    form.append("format", fmt);

    setLoading(true);
    console.log(`[app.js] Calling convert API with format: ${fmt}`);

    let res, blob, url;
    try {
      res = await fetch("/api/convert", {
        method: "POST",
        body: form
      });
      console.log("[app.js] Fetch response received:", res);

      if (!res.ok) {
        let errorDetail = `خطا در تبدیل: ${res.status}`;
        try {
            const errorData = await res.json();
            errorDetail = errorData.detail || errorData.message || errorDetail;
            console.error("[app.js] Server error JSON:", errorData);
        } catch (e) {
            const errorText = await res.text();
            console.error("[app.js] Server error, not JSON or failed to parse. Raw text:", errorText);
            errorDetail = errorText || errorDetail;
        }
        throw new Error(errorDetail);
      }

      blob = await res.blob();
      console.log("[app.js] Blob received:", blob);
      url = URL.createObjectURL(blob);
      objectUrls.add(url); // Add to global set for tracking and later revocation
      console.log("[app.js] Added to objectUrls:", url, "Current objectUrls size:", objectUrls.size);


    } catch (err) {
      console.error("[app.js] Conversion error in app.js (catch block):", err);
      alert(err.message || "خطایی رخ داد. لطفاً دوباره تلاش کنید.");
      // Do not revoke URL here if error happens after createObjectURL, as it's already added to objectUrls
      return null;
    } finally {
      setLoading(false);
    }
    console.log("[app.js] Conversion successful, URL:", url);
    return url;
  }

  // --- Helper to create consistent filename-safe timestamps ---
  function getFormattedTimestamp(forFile = false) {
    const date = new Date();
    const optionsDisplay = { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" };
    const optionsFile = { // More suitable for filenames
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    };

    if (forFile) {
        try {
            // Generates something like 2023-05-17_14-30-55
            return date.toLocaleDateString('sv', optionsFile).replace(/\//g, '-') + '_' + date.toLocaleTimeString('sv', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(/:/g, '-');
        } catch (e) { // Fallback for 'sv' locale issues
            return date.toISOString().replace(/:/g, "-").slice(0, 19).replace("T", "_");
        }
    } else {
        try {
            return date.toLocaleString("fa-IR", optionsDisplay);
        } catch (e) {
            console.warn("[app.js] fa-IR locale not fully supported for date formatting, using default.");
            return date.toLocaleString(undefined, optionsDisplay);
        }
    }
  }

  // --- Helper to get text snippet ---
  function getTextSnippet(text) {
    if (!text) return "";
    return text.trim().slice(0, 50).replace(/\s+/g, " ");
  }

  // --- DOCX button: ---
  if (btnDocx) {
    btnDocx.onclick = async () => {
      console.log("[app.js] btnDocx clicked");
      if (!inp) {
        console.error("[app.js] Input element not found for DOCX conversion.");
        alert("خطای داخلی: عنصر ورودی یافت نشد.");
        return;
      }
      const docxUrl = await convert("docx"); // This gets the blob: URL and adds it to objectUrls
      console.log("[app.js] docxUrl from convert:", docxUrl);

      if (!docxUrl) {
          console.log("[app.js] docxUrl is null, exiting btnDocx.onclick");
          return;
      }

      // --- For IMMEDIATE automatic download ---
      const tempLink = document.createElement('a');
      tempLink.href = docxUrl;
      // Use a timestamp or a more dynamic name for downloaded file
      const downloadFileName = `FarsiText_${getFormattedTimestamp(true)}.docx`;
      tempLink.setAttribute('download', downloadFileName);
      document.body.appendChild(tempLink); // Required for Firefox
      tempLink.click();
      document.body.removeChild(tempLink); // Clean up the temporary link
      console.log("[app.js] Automatic download initiated for DOCX:", downloadFileName);
      // We do NOT revoke docxUrl here because it's stored in history and managed by objectUrls Set.


      const displayTimestamp = getFormattedTimestamp(); // For display in history
      const entry = {
        time: displayTimestamp,
        snip: getTextSnippet(inp.value),
        docx: docxUrl, // Store the blob URL (already added to objectUrls)
      };

      history.push(entry);
      if (history.length > 20) { // Max history items
        const removedEntry = history.shift();
        if (removedEntry.docx) {
          // Only revoke if this specific URL is no longer referenced elsewhere
          // For simplicity, we assume if it's removed from history, it can be revoked.
          // More robustly, one might use a reference counter for blob URLs.
          console.log("[app.js] Removing old history entry, revoking URL:", removedEntry.docx);
          URL.revokeObjectURL(removedEntry.docx);
          objectUrls.delete(removedEntry.docx); // Remove from our tracking set
          console.log("[app.js] Current objectUrls size after removing old history:", objectUrls.size);
        }
      }
      saveHistory();
      renderHistory();
      console.log("[app.js] History updated for DOCX");
    };
  }


  // --- Initial render ---
  renderHistory();

  // Handle page unload to clean up object URLs
  window.addEventListener('beforeunload', () => {
    console.log("[app.js] beforeunload event: Revoking ALL object URLs. Current count:", objectUrls.size);
    objectUrls.forEach(url => {
        console.log("[app.js] Revoking URL on page unload:", url);
        URL.revokeObjectURL(url);
    });
    objectUrls.clear(); // Clear the set
  });

})();