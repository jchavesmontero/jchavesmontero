(() => {
  const badges = [...document.querySelectorAll("[data-ads-doi]")];
  if (!badges.length) return;

  const normalizeDoi = value => String(value || "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, "");

  const script = document.currentScript;
  const snapshotUrl = new URL("data/ads-profile.json", script.src);
  const number = new Intl.NumberFormat("en-US");

  fetch(snapshotUrl, {cache: "no-store"})
    .then(response => {
      if (!response.ok) throw new Error("ADS snapshot unavailable");
      return response.json();
    })
    .then(profile => {
      const records = Array.isArray(profile.publication_citations) ? profile.publication_citations : [];
      badges.forEach(badge => {
        const doi = normalizeDoi(badge.dataset.adsDoi);
        const record = records.find(item =>
          (item.dois || []).some(candidate => normalizeDoi(candidate) === doi)
        );
        if (!record) {
          badge.textContent = "ADS record unavailable";
          return;
        }
        badge.textContent = `${number.format(record.citations)} citation${record.citations === 1 ? "" : "s"}`;
        badge.classList.remove("unavailable");
        badge.title = `Citation count from NASA/ADS · synced ${profile.updated}`;
      });
    })
    .catch(() => {
      badges.forEach(badge => { badge.textContent = "Citation data unavailable"; });
    });
})();
