// Early-access signup form. Posts to the Google Apps Script web app set in
// projects.json (site.form_endpoint) and shows a "you're in" panel on success.
(function () {
  "use strict";

  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function phoneDigits(value) {
    return value.replace(/[^\d]/g, "");
  }

  function source() {
    var params = new URLSearchParams(location.search);
    var ref = params.get("ref") || params.get("from") || params.get("utm_source");
    if (ref) return ref.slice(0, 60);
    try {
      if (document.referrer) return new URL(document.referrer).hostname;
    } catch (e) {}
    return "direct";
  }

  function remember(slug, position) {
    try { localStorage.setItem("ea:" + slug, JSON.stringify({ position: position || null })); } catch (e) {}
  }

  function recall(slug) {
    try { return JSON.parse(localStorage.getItem("ea:" + slug) || "null"); } catch (e) { return null; }
  }

  function showDone(form, position, already) {
    var section = form.parentElement;
    var done = section.querySelector(".done");
    var pos = done.querySelector(".position");
    if (position) {
      pos.textContent = already
        ? "You were already on the list: #" + position + "."
        : "You're #" + position + " on the waitlist.";
    } else if (already) {
      pos.textContent = "You're already on the list.";
    }
    form.hidden = true;
    done.hidden = false;
    document.documentElement.classList.add("joined");
    updateFloat();
  }

  function setup(form) {
    var slug = form.dataset.project;
    var status = form.querySelector(".status");
    var button = form.querySelector("button[type=submit]");
    var label = button.textContent;

    var saved = recall(slug);
    if (saved) showDone(form, saved.position, true);

    function say(message, isError) {
      status.textContent = message;
      status.classList.toggle("error", Boolean(isError));
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var email = form.email.value.trim();
      var phone = form.phone.value.trim();
      var name = form.name.value.trim();

      if (form.website.value) { showDone(form); return; } // bot filled the hidden field
      if (!email && !phone) { say("Add your email or phone number.", true); form.email.focus(); return; }
      if (email && !EMAIL.test(email)) { say("That email doesn't look right.", true); form.email.focus(); return; }
      var digits = phoneDigits(phone);
      if (phone && (digits.length < 8 || digits.length > 15)) {
        say("Add the full phone number, with country code (like +91).", true); form.phone.focus(); return;
      }
      if (!form.dataset.endpoint) { say("Signups aren't connected yet. Please try again soon.", true); return; }

      var body = new URLSearchParams({
        project: slug,
        project_name: form.dataset.projectName || slug,
        email: email,
        phone: phone,
        name: name,
        ref: source(),
        page: location.href.split("#")[0]
      });

      button.disabled = true;
      button.textContent = "Joining…";
      say("");

      fetch(form.dataset.endpoint, { method: "POST", body: body })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!data || !data.ok) throw new Error((data && data.error) || "server");
          remember(slug, data.position);
          showDone(form, data.position, data.status === "exists");
        })
        .catch(function (err) {
          if (err instanceof TypeError) {
            // The browser blocked reading the reply (CORS). Send it without reading the answer.
            return fetch(form.dataset.endpoint, { method: "POST", body: body, mode: "no-cors" })
              .then(function () { remember(slug); showDone(form); });
          }
          throw err;
        })
        .catch(function (err) {
          var known = err && err.message && err.message !== "server" ? err.message : null;
          say(known || "Something went wrong. Please try again in a moment.", true);
        })
        .finally(function () {
          button.disabled = false;
          button.textContent = label;
        });
    });
  }

  // Floating "Get early access" button: shown once the hero button scrolls away,
  // hidden while the form is on screen or after the visitor has signed up.
  var floatCta = document.querySelector(".float-cta");
  var visible = { hero: true, join: false };

  function updateFloat() {
    if (!floatCta) return;
    var show = !visible.hero && !visible.join && !document.documentElement.classList.contains("joined");
    floatCta.classList.toggle("show", show);
    floatCta.setAttribute("aria-hidden", show ? "false" : "true");
    floatCta.tabIndex = show ? 0 : -1;
  }

  function goToForm(event) {
    var join = document.getElementById("join");
    var email = join && join.querySelector("input[name=email]");
    if (!join) return;
    event.preventDefault();
    join.scrollIntoView({ behavior: "smooth", block: "start" });
    if (email && !join.querySelector("form").hidden) {
      setTimeout(function () { email.focus({ preventScroll: true }); }, 450);
    }
  }

  if (floatCta && "IntersectionObserver" in window) {
    var hero = document.querySelector(".hero .jump");
    var join = document.getElementById("join");
    var watch = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        visible[entry.target === hero ? "hero" : "join"] = entry.isIntersecting;
      });
      updateFloat();
    }, { rootMargin: "0px 0px -10% 0px" });
    if (hero) watch.observe(hero);
    if (join) watch.observe(join);
  }
  document.querySelectorAll('a[href="#join"]').forEach(function (link) {
    link.addEventListener("click", goToForm);
  });

  // Fade sections in as they scroll into view.
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    document.documentElement.classList.add("reveal-ready");
    var show = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("in"); show.unobserve(entry.target); }
      });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { show.observe(el); });
  }

  document.querySelectorAll("form.signup").forEach(setup);
})();
