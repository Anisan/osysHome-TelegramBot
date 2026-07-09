(function () {
  var DEFAULT_AVATAR_URL = "/TelegramBot/static/TelegramBot.png";

  function getAvatarMap(selectEl) {
    var map = {};
    Array.prototype.forEach.call(selectEl.options, function (opt) {
      map[String(opt.value)] = {
        avatarUrl: opt.dataset.avatarUrl || "",
        text: opt.textContent || String(opt.value)
      };
    });
    return map;
  }

  function avatarNode(meta) {
    var img = document.createElement("img");
    img.className = "tlg-choice-avatar";
    if (meta && meta.avatarUrl) {
      img.src = meta.avatarUrl;
      img.alt = "";
      img.onerror = function () {
        if (img.src.indexOf(DEFAULT_AVATAR_URL) === -1) {
          img.src = DEFAULT_AVATAR_URL;
          return;
        }
        img.classList.add("tlg-choice-avatar-fallback");
      };
    } else {
      img.src = DEFAULT_AVATAR_URL;
      img.alt = "";
      img.onerror = function () {
        img.classList.add("tlg-choice-avatar-fallback");
      };
    }
    return img;
  }

  function decorateItems(wrapper, avatarMap) {
    var dropdownItems = wrapper.querySelectorAll(".choices__list--dropdown .choices__item--choice[data-value]");
    dropdownItems.forEach(function (item) {
      if (item.querySelector(".tlg-choice-option")) return;
      var value = String(item.dataset.value || "");
      var meta = avatarMap[value] || { text: item.textContent || value, avatarUrl: "" };
      var text = item.textContent;
      item.textContent = "";
      var row = document.createElement("div");
      row.className = "tlg-choice-option";
      var name = document.createElement("span");
      name.className = "tlg-choice-name";
      name.textContent = text;
      row.appendChild(avatarNode(meta));
      row.appendChild(name);
      item.appendChild(row);
    });

    var selectedItems = wrapper.querySelectorAll(".choices__list--multiple .choices__item[data-value]");
    selectedItems.forEach(function (item) {
      if (item.querySelector(".tlg-choice-item")) return;
      var value = String(item.dataset.value || "");
      var meta = avatarMap[value] || { text: item.textContent || value, avatarUrl: "" };
      var removeBtn = item.querySelector("button");
      var text = item.childNodes[0] ? item.childNodes[0].textContent : meta.text;
      item.textContent = "";
      var row = document.createElement("div");
      row.className = "tlg-choice-item";
      var name = document.createElement("span");
      name.className = "tlg-choice-name";
      name.textContent = text.trim();
      row.appendChild(avatarNode(meta));
      row.appendChild(name);
      item.appendChild(row);
      if (removeBtn) item.appendChild(removeBtn);
    });
  }

  function insertActions(wrapper, choices, selectEl) {
    var dropdown = wrapper.querySelector(".choices__list--dropdown");
    if (!dropdown || dropdown.querySelector(".tlg-choices-actions")) return;

    var actions = document.createElement("div");
    actions.className = "tlg-choices-actions";

    var selectAllBtn = document.createElement("button");
    selectAllBtn.type = "button";
    selectAllBtn.className = "btn btn-sm btn-outline-primary";
    selectAllBtn.textContent = selectEl.dataset.selectAllLabel || "Select all";
    selectAllBtn.addEventListener("click", function () {
      var values = [];
      Array.prototype.forEach.call(selectEl.options, function (opt) {
        if (!opt.disabled) values.push(String(opt.value));
      });
      choices.removeActiveItems();
      choices.setChoiceByValue(values);
      decorateItems(wrapper, getAvatarMap(selectEl));
    });

    var clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "btn btn-sm btn-outline-secondary";
    clearBtn.textContent = selectEl.dataset.clearLabel || "Clear";
    clearBtn.addEventListener("click", function () {
      choices.removeActiveItems();
      decorateItems(wrapper, getAvatarMap(selectEl));
    });

    actions.appendChild(selectAllBtn);
    actions.appendChild(clearBtn);
    dropdown.insertBefore(actions, dropdown.firstChild);
  }

  function initOne(selectEl) {
    if (!selectEl) return;
    if (!window.Choices) {
      selectEl.classList.remove("tlg-awaiting-choices");
      return;
    }

    var avatarMap = getAvatarMap(selectEl);
    var instance = new window.Choices(selectEl, {
      removeItemButton: true,
      searchEnabled: true,
      searchResultLimit: 1000,
      shouldSort: false,
      itemSelectText: ""
    });

    var wrapper = selectEl.closest(".choices");
    if (!wrapper) {
      selectEl.classList.remove("tlg-awaiting-choices");
      return;
    }

    function refreshUI() {
      decorateItems(wrapper, avatarMap);
      insertActions(wrapper, instance, selectEl);
    }

    refreshUI();
    selectEl.addEventListener("showDropdown", refreshUI);
    selectEl.addEventListener("addItem", refreshUI);
    selectEl.addEventListener("removeItem", refreshUI);
    selectEl.addEventListener("search", refreshUI);

    var observer = new MutationObserver(refreshUI);
    observer.observe(wrapper, { childList: true, subtree: true });

    selectEl.classList.remove("tlg-awaiting-choices");
  }

  function initAll() {
    initOne(document.getElementById("users"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
