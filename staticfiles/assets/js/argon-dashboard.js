"use strict";
(function () {
  var isWindows = navigator.platform.indexOf("Win") > -1 ? true : false;

  if (isWindows) {
    // if we are on windows OS we activate the perfectScrollbar function
    if (document.getElementsByClassName("main-content")[0]) {
      var mainpanel = document.querySelector(".main-content");
      var ps = new PerfectScrollbar(mainpanel);
    }

    if (document.getElementsByClassName("sidenav")[0]) {
      var sidebar = document.querySelector(".sidenav");
      var ps1 = new PerfectScrollbar(sidebar);
    }

    if (document.getElementsByClassName("navbar-collapse")[0]) {
      var fixedplugin = document.querySelector(
        ".navbar:not(.navbar-expand-lg) .navbar-collapse"
      );
      var ps2 = new PerfectScrollbar(fixedplugin);
    }

    if (document.getElementsByClassName("fixed-plugin")[0]) {
      var fixedplugin = document.querySelector(".fixed-plugin");
      var ps3 = new PerfectScrollbar(fixedplugin);
    }
  }
})();

function mapDefaultLocation() {
  var osm = L.tileLayer("http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
    mqi = L.tileLayer("http://{s}.mqcdn.com/tiles/1.0.0/sat/{z}/{x}/{y}.png", {
      subdomains: ["otile1", "otile2", "otile3", "otile4"],
    });
  var map = L.map("map", {
    layers: [osm, mqi],
  }).setView([-1.9507, 30.0663], 11);

  var baseMaps = {
    OpenStreetMap: osm,
    "OpenStreetMap.HOT": osmHOT,
  };

  var overlayMaps = {};

  var layerControl = L.control.layers(baseMaps, overlayMaps).addTo(map);

  var openTopoMap = L.tileLayer(
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        "Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)",
    }
  );

  layerControl.addBaseLayer(openTopoMap, "OpenTopoMap");
  layerControl.addOverlay(parks, "Parks");

  L.marker([-1.9507, 30.0663])
    .addTo(map)
    .bindPopup("Your current location.")
    .openPopup();
}

// invoke leaflet map
if (document.getElementById("map")) {
  // request access to location, otherwise use default location
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function (position) {
        var osm = L.tileLayer(
          "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          {
            maxZoom: 19,
            attribution: "© OpenStreetMap",
          }
        );

        var googleSat = L.tileLayer(
          "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
          {
            maxZoom: 20,
            attribution: "© Google",
          }
        );

        var map = L.map("map", {
          layers: [osm],
        }).setView([position.coords.latitude, position.coords.longitude], 11);

        var baseMaps = {
          OpenStreetMap: osm,
          "Google Satellite": googleSat,
        };

        var overlayMaps = {};

        L.control.layers(baseMaps, overlayMaps).addTo(map);

        // Add OpenStreetMap tile layer
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 18,
        }).addTo(map);

        // Define custom icons for markers
        var greenIcon = L.icon({
          iconUrl: "/static/assets/img/green-pin.png",
          iconSize: [38, 95],
          shadowSize: [50, 64],
          iconAnchor: [22, 94],
          shadowAnchor: [4, 62],
          popupAnchor: [-3, -76],
        });

        var redIcon = L.icon({
          iconUrl: "/static/assets/img/red-pin.png",
          iconSize: [20, 20],
          shadowSize: [20, 20],
          iconAnchor: [22, 94],
          shadowAnchor: [4, 62],
          popupAnchor: [-3, -76],
        });

        // Create markers for each feature
        var geoJsonLayer = L.geoJson(null, {
          pointToLayer: function (feature, latlng) {
            var icon = feature.properties.is_eudr_compliant
              ? greenIcon
              : redIcon;
            return L.marker(latlng, { icon: icon });
          },
          onEachFeature: function (feature, layer) {
            var popupContent = `
          <b>Farmer Name:</b> ${feature.properties.farmer_name}<br>
          <b>Farm Size:</b> ${feature.properties.farm_size}<br>
          <b>Collection Site:</b> ${feature.properties.collection_site}<br>
          <b>Farm Village:</b> ${feature.properties.farm_village}<br>
          <b>Plantation Name:</b> ${feature.properties.plantation_name}<br>
          <b>Plantation Code:</b> ${feature.properties.plantation_code}<br>
          <b>Validated:</b> ${
            feature.properties.is_validated ? "Yes" : "No"
          }<br>
          <b>EUDR Compliant:</b> ${
            feature.properties.is_eudr_compliant ? "Yes" : "No"
          }<br>
          <b>Created At:</b> ${feature.properties.created_at}<br>
          <b>Updated At:</b> ${feature.properties.updated_at}
      `;
            layer.bindPopup(popupContent);
          },
        }).addTo(map);

        // Add legend
        var legend = L.control({ position: "bottomright" });
        legend.onAdd = function (map) {
          var div = L.DomUtil.create("div", "legend");
          // add background color to legend, shadow, border radius, and padding
          div.style.backgroundColor = "rgba(255, 255, 255, 0.8)";
          div.style.boxShadow = "0 1px 5px rgba(0, 0, 0, 0.4)";
          div.style.borderRadius = "5px";
          div.style.padding = "10px";
          div.innerHTML += "<h6>Legend</h6>";
          div.innerHTML +=
            "<p class='fs-6'><img src='/static/assets/img/green-pin.png' alt='green pin' style='width: 20px; height: 20px;'> EUDR Compliant</p>";
          div.innerHTML +=
            "<p class='fs-6'><img src='/static/assets/img/red-pin.png' alt='green pin' style='width: 20px; height: 20px;'> Not EUDR Compliant</p>";

          return div;
        };
        legend.addTo(map);

        // Load GeoJSON data
        var geojsonData = [
          {
            type: "Feature",
            properties: {
              farmer_name: "John Doe",
              farm_size: 10.5,
              collection_site: "Site A",
              farm_village: "Village A",
              plantation_name: "Plantation A",
              plantation_code: "P123",
              is_validated: true,
              is_eudr_compliant: false,
              created_at: "2024-04-15T07:39:59.337432Z",
              updated_at: "2024-04-15T07:39:59.337432Z",
            },
            geometry: {
              type: "MultiPolygon",
              coordinates: [
                [
                  [
                    [2.403637000523464, 9.808962999547964],
                    [2.403526999225821, 9.808952000034356],
                    [2.403400000302579, 9.808956999635576],
                    [2.403272999830111, 9.808970000600517],
                    [2.403147000036964, 9.809019999530923],
                    [2.403037999995064, 9.809063000085501],
                    [2.402905000139508, 9.809071999136428],
                    [2.40277300038654, 9.809101999649894],
                    [2.402646999597414, 9.809152999579267],
                    [2.402519999556543, 9.809182000369692],
                    [2.402390000414746, 9.809213000022243],
                    [2.402268000130128, 9.809242000483529],
                    [2.4021469999294, 9.809292999990461],
                    [2.402175000064603, 9.809414999678843],
                    [2.402233000208718, 9.80951700034007],
                    [2.40223500039765, 9.809646999913321],
                    [2.402246999876439, 9.80976699974824],
                    [2.402283000296378, 9.80989999953533],
                    [2.402298000082538, 9.810027000353925],
                    [2.402282999891717, 9.810146999616473],
                    [2.402312000707739, 9.81027700066214],
                    [2.402298000015546, 9.810399999840794],
                    [2.402288000021151, 9.810533000826808],
                    [2.402304999949636, 9.810671999599133],
                    [2.402336999748919, 9.810795000284525],
                    [2.402353000596902, 9.81091499993108],
                    [2.402376999622676, 9.811038000074564],
                    [2.402396999296453, 9.811164999751025],
                    [2.402434999387635, 9.811289999827594],
                    [2.402462000205962, 9.811408000191697],
                    [2.402571999937241, 9.81143199933343],
                    [2.402682000077364, 9.811411999265584],
                    [2.402802999797487, 9.811379999688748],
                    [2.402928000140625, 9.811354999192485],
                    [2.403051999799465, 9.811319999416803],
                    [2.403173000709951, 9.811297999889364],
                    [2.403287000070256, 9.811272000400985],
                    [2.403372000037872, 9.81119799923909],
                    [2.403360000269459, 9.811081999681722],
                    [2.403347000073796, 9.81096300020695],
                    [2.40332700052714, 9.810850000099316],
                    [2.403309999982164, 9.810731999298236],
                    [2.403296999430051, 9.810602000250826],
                    [2.403270000716033, 9.810473000368672],
                    [2.403350000057729, 9.810408000238754],
                    [2.403478000143298, 9.8103849999472],
                    [2.403604999993024, 9.810364999620555],
                    [2.403707000225672, 9.810329999767408],
                    [2.403733000481938, 9.810226999363994],
                    [2.403719999220036, 9.810106999600155],
                    [2.403704999867739, 9.8099820002986],
                    [2.403686999727203, 9.809861999880836],
                    [2.403672999986336, 9.809742000167136],
                    [2.403629999870178, 9.809619999511776],
                    [2.403595000143266, 9.809511999798852],
                    [2.403611999846758, 9.80939999995004],
                    [2.403626999817904, 9.80926300018786],
                    [2.403627999675904, 9.809148000265127],
                    [2.403613000256115, 9.809045000098992],
                    [2.403637000523464, 9.808962999547964],
                  ],
                ],
              ],
            },
          },
        ];

        geoJsonLayer.addData(geojsonData);

        L.marker([position.coords.latitude, position.coords.longitude])
          .addTo(map)
          .bindPopup("Your current location.")
          .openPopup();
      },
      function () {
        mapDefaultLocation();
      }
    );
  } else {
    mapDefaultLocation();
  }
}

// Verify navbar blur on scroll
if (document.getElementById("navbarBlur")) {
  navbarBlurOnScroll("navbarBlur");
}

// initialization of Tooltips
var tooltipTriggerList = [].slice.call(
  document.querySelectorAll('[data-bs-toggle="tooltip"]')
);
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl);
});

// when input is focused add focused class for style
function focused(el) {
  if (el.parentElement.classList.contains("input-group")) {
    el.parentElement.classList.add("focused");
  }
}

// when input is focused remove focused class for style
function defocused(el) {
  if (el.parentElement.classList.contains("input-group")) {
    el.parentElement.classList.remove("focused");
  }
}

// helper for adding on all elements multiple attributes
function setAttributes(el, options) {
  Object.keys(options).forEach(function (attr) {
    el.setAttribute(attr, options[attr]);
  });
}

// adding on inputs attributes for calling the focused and defocused functions
if (document.querySelectorAll(".input-group").length != 0) {
  var allInputs = document.querySelectorAll("input.form-control");
  allInputs.forEach((el) =>
    setAttributes(el, {
      onfocus: "focused(this)",
      onfocusout: "defocused(this)",
    })
  );
}

// Fixed Plugin
if (document.querySelector(".fixed-plugin")) {
  var fixedPlugin = document.querySelector(".fixed-plugin");
  var fixedPluginButton = document.querySelector(".fixed-plugin-button");
  var fixedPluginButtonNav = document.querySelector(".fixed-plugin-button-nav");
  var fixedPluginCard = document.querySelector(".fixed-plugin .card");
  var fixedPluginCloseButton = document.querySelectorAll(
    ".fixed-plugin-close-button"
  );
  var navbar = document.getElementById("navbarBlur");
  var buttonNavbarFixed = document.getElementById("navbarFixed");

  if (fixedPluginButton) {
    fixedPluginButton.onclick = function () {
      if (!fixedPlugin.classList.contains("show")) {
        fixedPlugin.classList.add("show");
      } else {
        fixedPlugin.classList.remove("show");
      }
    };
  }

  if (fixedPluginButtonNav) {
    fixedPluginButtonNav.onclick = function () {
      if (!fixedPlugin.classList.contains("show")) {
        fixedPlugin.classList.add("show");
      } else {
        fixedPlugin.classList.remove("show");
      }
    };
  }

  fixedPluginCloseButton.forEach(function (el) {
    el.onclick = function () {
      fixedPlugin.classList.remove("show");
    };
  });

  document.querySelector("body").onclick = function (e) {
    if (
      e.target != fixedPluginButton &&
      e.target != fixedPluginButtonNav &&
      e.target.closest(".fixed-plugin .card") != fixedPluginCard
    ) {
      fixedPlugin.classList.remove("show");
    }
  };

  if (navbar) {
    if (navbar.getAttribute("data-scroll") == "true" && buttonNavbarFixed) {
      buttonNavbarFixed.setAttribute("checked", "true");
    }
  }
}

//Set Sidebar Color
function sidebarColor(a) {
  var parent = a.parentElement.children;
  var color = a.getAttribute("data-color");

  for (var i = 0; i < parent.length; i++) {
    parent[i].classList.remove("active");
  }

  if (!a.classList.contains("active")) {
    a.classList.add("active");
  } else {
    a.classList.remove("active");
  }

  var sidebar = document.querySelector(".sidenav");
  sidebar.setAttribute("data-color", color);

  if (document.querySelector("#sidenavCard")) {
    var sidenavCard = document.querySelector("#sidenavCard+.btn+.btn");
    let sidenavCardClasses = [
      "btn",
      "btn-sm",
      "w-100",
      "mb-0",
      "bg-gradient-" + color,
    ];
    sidenavCard.removeAttribute("class");
    sidenavCard.classList.add(...sidenavCardClasses);
  }
}

// Set Sidebar Type
function sidebarType(a) {
  var parent = a.parentElement.children;
  var color = a.getAttribute("data-class");
  var body = document.querySelector("body");
  var bodyWhite = document.querySelector("body:not(.dark-version)");
  var bodyDark = body.classList.contains("dark-version");

  var colors = [];

  for (var i = 0; i < parent.length; i++) {
    parent[i].classList.remove("active");
    colors.push(parent[i].getAttribute("data-class"));
  }

  if (!a.classList.contains("active")) {
    a.classList.add("active");
  } else {
    a.classList.remove("active");
  }

  var sidebar = document.querySelector(".sidenav");

  for (var i = 0; i < colors.length; i++) {
    sidebar.classList.remove(colors[i]);
  }

  sidebar.classList.add(color);

  // Remove text-white/text-dark classes
  if (color == "bg-white") {
    var textWhites = document.querySelectorAll(".sidenav .text-white");
    for (let i = 0; i < textWhites.length; i++) {
      textWhites[i].classList.remove("text-white");
      textWhites[i].classList.add("text-dark");
    }
  } else {
    var textDarks = document.querySelectorAll(".sidenav .text-dark");
    for (let i = 0; i < textDarks.length; i++) {
      textDarks[i].classList.add("text-white");
      textDarks[i].classList.remove("text-dark");
    }
  }

  if (color == "bg-default" && bodyDark) {
    var textDarks = document.querySelectorAll(".navbar-brand .text-dark");
    for (let i = 0; i < textDarks.length; i++) {
      textDarks[i].classList.add("text-white");
      textDarks[i].classList.remove("text-dark");
    }
  }

  // Remove logo-white/logo-dark

  if (color == "bg-white" && bodyWhite) {
    var navbarBrand = document.querySelector(".navbar-brand-img");
    var navbarBrandImg = navbarBrand.src;

    if (navbarBrandImg.includes("logo-ct.png")) {
      var navbarBrandImgNew = navbarBrandImg.replace("logo-ct", "logo-ct-dark");
      navbarBrand.src = navbarBrandImgNew;
    }
  } else {
    var navbarBrand = document.querySelector(".navbar-brand-img");
    var navbarBrandImg = navbarBrand.src;
    if (navbarBrandImg.includes("logo-ct-dark.png")) {
      var navbarBrandImgNew = navbarBrandImg.replace("logo-ct-dark", "logo-ct");
      navbarBrand.src = navbarBrandImgNew;
    }
  }

  if (color == "bg-white" && bodyDark) {
    var navbarBrand = document.querySelector(".navbar-brand-img");
    var navbarBrandImg = navbarBrand.src;

    if (navbarBrandImg.includes("logo-ct.png")) {
      var navbarBrandImgNew = navbarBrandImg.replace("logo-ct", "logo-ct-dark");
      navbarBrand.src = navbarBrandImgNew;
    }
  }
}

// Set Navbar Fixed
function navbarFixed(el) {
  let classes = [
    "position-sticky",
    "bg-white",
    "left-auto",
    "top-2",
    "z-index-sticky",
  ];
  const navbar = document.getElementById("navbarBlur");

  if (!el.getAttribute("checked")) {
    toggleNavLinksColor("blur");
    navbar.classList.add(...classes);
    navbar.setAttribute("data-scroll", "true");
    navbarBlurOnScroll("navbarBlur");
    el.setAttribute("checked", "true");
  } else {
    toggleNavLinksColor("transparent");
    navbar.classList.remove(...classes);
    navbar.setAttribute("data-scroll", "false");
    navbarBlurOnScroll("navbarBlur");
    el.removeAttribute("checked");
  }
}

// Set Navbar Minimized
function navbarMinimize(el) {
  var sidenavShow = document.getElementsByClassName("g-sidenav-show")[0];

  if (!el.getAttribute("checked")) {
    sidenavShow.classList.remove("g-sidenav-pinned");
    sidenavShow.classList.add("g-sidenav-hidden");
    el.setAttribute("checked", "true");
  } else {
    sidenavShow.classList.remove("g-sidenav-hidden");
    sidenavShow.classList.add("g-sidenav-pinned");
    el.removeAttribute("checked");
  }
}

function toggleNavLinksColor(type) {
  let navLinks = document.querySelectorAll(
    ".navbar-main .nav-link, .navbar-main .breadcrumb-item, .navbar-main .breadcrumb-item a, .navbar-main h6"
  );
  let navLinksToggler = document.querySelectorAll(
    ".navbar-main .sidenav-toggler-line"
  );

  if (type === "blur") {
    navLinks.forEach((element) => {
      element.classList.remove("text-white");
    });

    navLinksToggler.forEach((element) => {
      element.classList.add("bg-dark");
      element.classList.remove("bg-white");
    });
  } else if (type === "transparent") {
    navLinks.forEach((element) => {
      element.classList.add("text-white");
    });

    navLinksToggler.forEach((element) => {
      element.classList.remove("bg-dark");
      element.classList.add("bg-white");
    });
  }
}

// Navbar blur on scroll
function navbarBlurOnScroll(id) {
  const navbar = document.getElementById(id);
  let navbarScrollActive = navbar ? navbar.getAttribute("data-scroll") : false;
  let scrollDistance = 5;
  let classes = ["bg-white", "left-auto", "position-sticky"];
  let toggleClasses = ["shadow-none"];

  if (navbarScrollActive == "true") {
    window.onscroll = debounce(function () {
      if (window.scrollY > scrollDistance) {
        blurNavbar();
      } else {
        transparentNavbar();
      }
    }, 10);
  } else {
    window.onscroll = debounce(function () {
      transparentNavbar();
    }, 10);
  }

  var isWindows = navigator.platform.indexOf("Win") > -1 ? true : false;

  if (isWindows) {
    var content = document.querySelector(".main-content");
    if (navbarScrollActive == "true") {
      content.addEventListener(
        "ps-scroll-y",
        debounce(function () {
          if (content.scrollTop > scrollDistance) {
            blurNavbar();
          } else {
            transparentNavbar();
          }
        }, 10)
      );
    } else {
      content.addEventListener(
        "ps-scroll-y",
        debounce(function () {
          transparentNavbar();
        }, 10)
      );
    }
  }

  function blurNavbar() {
    navbar.classList.add(...classes);
    navbar.classList.remove(...toggleClasses);

    toggleNavLinksColor("blur");
  }

  function transparentNavbar() {
    navbar.classList.remove(...classes);
    navbar.classList.add(...toggleClasses);

    toggleNavLinksColor("transparent");
  }
}

// Debounce Function
// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
function debounce(func, wait, immediate) {
  var timeout;
  return function () {
    var context = this,
      args = arguments;
    var later = function () {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    var callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(context, args);
  };
}

// Toggle Sidenav
const iconNavbarSidenav = document.getElementById("iconNavbarSidenav");
const iconSidenav = document.getElementById("iconSidenav");
const sidenav = document.getElementById("sidenav-main");
let body = document.getElementsByTagName("body")[0];
let className = "g-sidenav-pinned";

if (iconNavbarSidenav) {
  iconNavbarSidenav.addEventListener("click", toggleSidenav);
}

if (iconSidenav) {
  iconSidenav.addEventListener("click", toggleSidenav);
}

function toggleSidenav() {
  if (body.classList.contains(className)) {
    body.classList.remove(className);
    setTimeout(function () {
      sidenav.classList.remove("bg-white");
    }, 100);
    sidenav.classList.remove("bg-transparent");
  } else {
    body.classList.add(className);
    sidenav.classList.add("bg-white");
    sidenav.classList.remove("bg-transparent");
    iconSidenav.classList.remove("d-none");
  }
}

let html = document.getElementsByTagName("html")[0];

html.addEventListener("click", function (e) {
  if (
    body.classList.contains("g-sidenav-pinned") &&
    !e.target.classList.contains("sidenav-toggler-line")
  ) {
    body.classList.remove(className);
  }
});

// Resize navbar color depends on configurator active type of sidenav

let referenceButtons = document.querySelector("[data-class]");

window.addEventListener("resize", navbarColorOnResize);

function navbarColorOnResize() {
  if (window.innerWidth > 1200) {
    if (
      referenceButtons.classList.contains("active") &&
      referenceButtons.getAttribute("data-class") === "bg-transparent"
    ) {
      sidenav.classList.remove("bg-white");
    } else {
      if (!body.classList.contains("dark-version")) {
        sidenav.classList.add("bg-white");
      }
    }
  } else {
    sidenav.classList.add("bg-white");
    sidenav.classList.remove("bg-transparent");
  }
}

// Deactivate sidenav type buttons on resize and small screens
window.addEventListener("resize", sidenavTypeOnResize);
window.addEventListener("load", sidenavTypeOnResize);

function sidenavTypeOnResize() {
  let elements = document.querySelectorAll('[onclick="sidebarType(this)"]');
  if (window.innerWidth < 1200) {
    elements.forEach(function (el) {
      el.classList.add("disabled");
    });
  } else {
    elements.forEach(function (el) {
      el.classList.remove("disabled");
    });
  }
}

// Tabs navigation

var total = document.querySelectorAll(".nav-pills");

total.forEach(function (item, i) {
  var moving_div = document.createElement("div");
  var first_li = item.querySelector("li:first-child .nav-link");
  var tab = first_li.cloneNode();
  tab.innerHTML = "-";

  moving_div.classList.add("moving-tab", "position-absolute", "nav-link");
  moving_div.appendChild(tab);
  item.appendChild(moving_div);

  var list_length = item.getElementsByTagName("li").length;

  moving_div.style.padding = "0px";
  moving_div.style.width =
    item.querySelector("li:nth-child(1)").offsetWidth + "px";
  moving_div.style.transform = "translate3d(0px, 0px, 0px)";
  moving_div.style.transition = ".5s ease";

  item.onmouseover = function (event) {
    let target = getEventTarget(event);
    let li = target.closest("li"); // get reference
    if (li) {
      let nodes = Array.from(li.closest("ul").children); // get array
      let index = nodes.indexOf(li) + 1;
      item.querySelector("li:nth-child(" + index + ") .nav-link").onclick =
        function () {
          moving_div = item.querySelector(".moving-tab");
          let sum = 0;
          if (item.classList.contains("flex-column")) {
            for (var j = 1; j <= nodes.indexOf(li); j++) {
              sum += item.querySelector("li:nth-child(" + j + ")").offsetHeight;
            }
            moving_div.style.transform = "translate3d(0px," + sum + "px, 0px)";
            moving_div.style.height = item.querySelector(
              "li:nth-child(" + j + ")"
            ).offsetHeight;
          } else {
            for (var j = 1; j <= nodes.indexOf(li); j++) {
              sum += item.querySelector("li:nth-child(" + j + ")").offsetWidth;
            }
            moving_div.style.transform = "translate3d(" + sum + "px, 0px, 0px)";
            moving_div.style.width =
              item.querySelector("li:nth-child(" + index + ")").offsetWidth +
              "px";
          }
        };
    }
  };
});

// Tabs navigation resize

window.addEventListener("resize", function (event) {
  total.forEach(function (item, i) {
    item.querySelector(".moving-tab").remove();
    var moving_div = document.createElement("div");
    var tab = item.querySelector(".nav-link.active").cloneNode();
    tab.innerHTML = "-";

    moving_div.classList.add("moving-tab", "position-absolute", "nav-link");
    moving_div.appendChild(tab);

    item.appendChild(moving_div);

    moving_div.style.padding = "0px";
    moving_div.style.transition = ".5s ease";

    let li = item.querySelector(".nav-link.active").parentElement;

    if (li) {
      let nodes = Array.from(li.closest("ul").children); // get array
      let index = nodes.indexOf(li) + 1;

      let sum = 0;
      if (item.classList.contains("flex-column")) {
        for (var j = 1; j <= nodes.indexOf(li); j++) {
          sum += item.querySelector("li:nth-child(" + j + ")").offsetHeight;
        }
        moving_div.style.transform = "translate3d(0px," + sum + "px, 0px)";
        moving_div.style.width =
          item.querySelector("li:nth-child(" + index + ")").offsetWidth + "px";
        moving_div.style.height = item.querySelector(
          "li:nth-child(" + j + ")"
        ).offsetHeight;
      } else {
        for (var j = 1; j <= nodes.indexOf(li); j++) {
          sum += item.querySelector("li:nth-child(" + j + ")").offsetWidth;
        }
        moving_div.style.transform = "translate3d(" + sum + "px, 0px, 0px)";
        moving_div.style.width =
          item.querySelector("li:nth-child(" + index + ")").offsetWidth + "px";
      }
    }
  });

  if (window.innerWidth < 991) {
    total.forEach(function (item, i) {
      if (!item.classList.contains("flex-column")) {
        item.classList.add("flex-column", "on-resize");
      }
    });
  } else {
    total.forEach(function (item, i) {
      if (item.classList.contains("on-resize")) {
        item.classList.remove("flex-column", "on-resize");
      }
    });
  }
});

function getEventTarget(e) {
  e = e || window.event;
  return e.target || e.srcElement;
}

// End tabs navigation

// Light Mode / Dark Mode
function darkMode(el) {
  const body = document.getElementsByTagName("body")[0];
  const hr = document.querySelectorAll("div:not(.sidenav) > hr");
  const sidebar = document.querySelector(".sidenav");
  const sidebarWhite = document.querySelectorAll(".sidenav.bg-white");
  const hr_card = document.querySelectorAll("div:not(.bg-gradient-dark) hr");
  const text_btn = document.querySelectorAll("button:not(.btn) > .text-dark");
  const text_span = document.querySelectorAll(
    "span.text-dark, .breadcrumb .text-dark"
  );
  const text_span_white = document.querySelectorAll("span.text-white");
  const text_strong = document.querySelectorAll("strong.text-dark");
  const text_strong_white = document.querySelectorAll("strong.text-white");
  const text_nav_link = document.querySelectorAll("a.nav-link.text-dark");
  const secondary = document.querySelectorAll(".text-secondary");
  const bg_gray_100 = document.querySelectorAll(".bg-gray-100");
  const bg_gray_600 = document.querySelectorAll(".bg-gray-600");
  const btn_text_dark = document.querySelectorAll(
    ".btn.btn-link.text-dark, .btn .ni.text-dark"
  );
  const btn_text_white = document.querySelectorAll(
    ".btn.btn-link.text-white, .btn .ni.text-white"
  );
  const card_border = document.querySelectorAll(".card.border");
  const card_border_dark = document.querySelectorAll(
    ".card.border.border-dark"
  );
  const svg = document.querySelectorAll("g");
  const navbarBrand = document.querySelector(".navbar-brand-img");
  const navbarBrandImg = navbarBrand.src;
  const navLinks = document.querySelectorAll(
    ".navbar-main .nav-link, .navbar-main .breadcrumb-item, .navbar-main .breadcrumb-item a, .navbar-main h6"
  );
  const cardNavLinksIcons = document.querySelectorAll(".card .nav .nav-link i");
  const cardNavSpan = document.querySelectorAll(".card .nav .nav-link span");

  if (!el.getAttribute("checked")) {
    body.classList.add("dark-version");
    if (navbarBrandImg.includes("logo-ct-dark.png")) {
      var navbarBrandImgNew = navbarBrandImg.replace("logo-ct-dark", "logo-ct");
      navbarBrand.src = navbarBrandImgNew;
    }
    for (var i = 0; i < cardNavLinksIcons.length; i++) {
      if (cardNavLinksIcons[i].classList.contains("text-dark")) {
        cardNavLinksIcons[i].classList.remove("text-dark");
        cardNavLinksIcons[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < cardNavSpan.length; i++) {
      if (cardNavSpan[i].classList.contains("text-sm")) {
        cardNavSpan[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < hr.length; i++) {
      if (hr[i].classList.contains("dark")) {
        hr[i].classList.remove("dark");
        hr[i].classList.add("light");
      }
    }
    for (var i = 0; i < hr_card.length; i++) {
      if (hr_card[i].classList.contains("dark")) {
        hr_card[i].classList.remove("dark");
        hr_card[i].classList.add("light");
      }
    }
    for (var i = 0; i < text_btn.length; i++) {
      if (text_btn[i].classList.contains("text-dark")) {
        text_btn[i].classList.remove("text-dark");
        text_btn[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < text_span.length; i++) {
      if (text_span[i].classList.contains("text-dark")) {
        text_span[i].classList.remove("text-dark");
        text_span[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < text_strong.length; i++) {
      if (text_strong[i].classList.contains("text-dark")) {
        text_strong[i].classList.remove("text-dark");
        text_strong[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < text_nav_link.length; i++) {
      if (text_nav_link[i].classList.contains("text-dark")) {
        text_nav_link[i].classList.remove("text-dark");
        text_nav_link[i].classList.add("text-white");
      }
    }
    for (var i = 0; i < secondary.length; i++) {
      if (secondary[i].classList.contains("text-secondary")) {
        secondary[i].classList.remove("text-secondary");
        secondary[i].classList.add("text-white");
        secondary[i].classList.add("opacity-8");
      }
    }
    for (var i = 0; i < bg_gray_100.length; i++) {
      if (bg_gray_100[i].classList.contains("bg-gray-100")) {
        bg_gray_100[i].classList.remove("bg-gray-100");
        bg_gray_100[i].classList.add("bg-gray-600");
      }
    }
    for (var i = 0; i < btn_text_dark.length; i++) {
      btn_text_dark[i].classList.remove("text-dark");
      btn_text_dark[i].classList.add("text-white");
    }
    for (var i = 0; i < sidebarWhite.length; i++) {
      sidebarWhite[i].classList.remove("bg-white");
    }
    for (var i = 0; i < svg.length; i++) {
      if (svg[i].hasAttribute("fill")) {
        svg[i].setAttribute("fill", "#fff");
      }
    }
    for (var i = 0; i < card_border.length; i++) {
      card_border[i].classList.add("border-dark");
    }
    el.setAttribute("checked", "true");
  } else {
    body.classList.remove("dark-version");
    sidebar.classList.add("bg-white");
    if (navbarBrandImg.includes("logo-ct.png")) {
      var navbarBrandImgNew = navbarBrandImg.replace("logo-ct", "logo-ct-dark");
      navbarBrand.src = navbarBrandImgNew;
    }
    for (var i = 0; i < navLinks.length; i++) {
      if (navLinks[i].classList.contains("text-dark")) {
        navLinks[i].classList.add("text-white");
        navLinks[i].classList.remove("text-dark");
      }
    }
    for (var i = 0; i < cardNavLinksIcons.length; i++) {
      if (cardNavLinksIcons[i].classList.contains("text-white")) {
        cardNavLinksIcons[i].classList.remove("text-white");
        cardNavLinksIcons[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < cardNavSpan.length; i++) {
      if (cardNavSpan[i].classList.contains("text-white")) {
        cardNavSpan[i].classList.remove("text-white");
      }
    }
    for (var i = 0; i < hr.length; i++) {
      if (hr[i].classList.contains("light")) {
        hr[i].classList.add("dark");
        hr[i].classList.remove("light");
      }
    }
    for (var i = 0; i < hr_card.length; i++) {
      if (hr_card[i].classList.contains("light")) {
        hr_card[i].classList.add("dark");
        hr_card[i].classList.remove("light");
      }
    }
    for (var i = 0; i < text_btn.length; i++) {
      if (text_btn[i].classList.contains("text-white")) {
        text_btn[i].classList.remove("text-white");
        text_btn[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < text_span_white.length; i++) {
      if (
        text_span_white[i].classList.contains("text-white") &&
        !text_span_white[i].closest(".sidenav") &&
        !text_span_white[i].closest(".card.bg-gradient-dark")
      ) {
        text_span_white[i].classList.remove("text-white");
        text_span_white[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < text_strong_white.length; i++) {
      if (text_strong_white[i].classList.contains("text-white")) {
        text_strong_white[i].classList.remove("text-white");
        text_strong_white[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < secondary.length; i++) {
      if (secondary[i].classList.contains("text-white")) {
        secondary[i].classList.remove("text-white");
        secondary[i].classList.remove("opacity-8");
        secondary[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < bg_gray_600.length; i++) {
      if (bg_gray_600[i].classList.contains("bg-gray-600")) {
        bg_gray_600[i].classList.remove("bg-gray-600");
        bg_gray_600[i].classList.add("bg-gray-100");
      }
    }
    for (var i = 0; i < svg.length; i++) {
      if (svg[i].hasAttribute("fill")) {
        svg[i].setAttribute("fill", "#252f40");
      }
    }
    for (var i = 0; i < btn_text_white.length; i++) {
      if (!btn_text_white[i].closest(".card.bg-gradient-dark")) {
        btn_text_white[i].classList.remove("text-white");
        btn_text_white[i].classList.add("text-dark");
      }
    }
    for (var i = 0; i < card_border_dark.length; i++) {
      card_border_dark[i].classList.remove("border-dark");
    }
    el.removeAttribute("checked");
  }
}
