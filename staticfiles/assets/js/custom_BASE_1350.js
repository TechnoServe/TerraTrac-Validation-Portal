// if mapMonde is loaded, ask for user's location and embed it in url
const mapMonde = document.querySelector("#mapMonde");
const base_url = window.location.href;
if (mapMonde) {
  // if user allows location, get it and embed it in the url, otherwise, use default location
  if (navigator.geolocation && !window.location.search) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        if (!base_url.includes("lat")) {
          window.location.href = `${base_url}?lat=${latitude}&lon=${longitude}`;
        }
      },
      (error) => {
        if (!base_url.includes("lat")) {
          window.location.href = `${base_url}?lat=0.0&lon=0.0`;
        }
      }
    );
  }
}

document
  .getElementById("logout")
  .addEventListener("click", async function (event) {
    event.preventDefault();

    const response = await fetch("/logout/", {
      method: "POST",
      headers: {
        Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
      },
    });
    if (response.ok) {
      // remove the user's token from the local storage
      localStorage.removeItem("terratracAuthToken");
      window.location.href = "/auth/login";
    } else {
      // if the response is 401, the user is not authenticated, redirect to the login page
      if (response.status === 401) {
        localStorage.removeItem("terratracAuthToken");
        window.location.href = "/auth/login";
      }
    }
  });

document.getElementById("profile").addEventListener("click", function () {
  window.location.href = profileUrl;
});

var win = navigator.platform.indexOf("Win") > -1;
if (win && document.querySelector("#sidenav-scrollbar")) {
  var options = {
    damping: "0.5",
  };
  Scrollbar.init(document.querySelector("#sidenav-scrollbar"), options);
}

function googleTranslateElementInit() {
  const lang = localStorage.getItem("terraTracLang") || "en";
  new google.translate.TranslateElement(
    {
      pageLanguage: "en",
    },
    "google_translate_element"
  );

  changeLanguage(lang);
}

// Function to change the language
function changeLanguage(lang) {
  var translateSelect = document.querySelector(".goog-te-combo");
  if (translateSelect) {
    translateSelect.value = lang;
    translateSelect.dispatchEvent(new Event("change"));

    // save the selected language in the local storage
    localStorage.setItem("terraTracLang", lang);
  }
}

// Event listener for language selection
document.querySelectorAll(".dropdown-item-lang").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    // if id is not recognized, go up the tree to find the id
    let id = e.target.id;
    if (id === "") {
      id = e.target.parentElement.parentElement.id;
    }

    changeLanguage(id);
  });
});

// Add 'active' class to the current menu item
let currentLocation = window.location.href;
let links = document.querySelectorAll(".nav-link");
const selectedDownloadFormat = document.querySelector("#templateFormat");

selectedDownloadFormat?.addEventListener("change", (e) => {
  const selectedFormat = e.target.value;

  if (selectedFormat !== "") {
    window.location.href = `/api/download-template?file_format=${encodeURIComponent(
      selectedFormat
    )}`;
  }
});

links.forEach((link) => {
  if (link.href === currentLocation) {
    link.classList.add("active");
    document.title = link.innerText;
  }
});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function uploadData() {
  const fileInput = document.getElementById("uploadFile");
  const file = fileInput.files[0];
  const format = file?.name?.split(".").pop().toLowerCase();
  const file_name = file?.name?.split(".")[0];

  document.querySelector("#modal-error-container").classList.add("d-none");

  try {
    const reader = new FileReader();
    reader.onload = function (e) {
      let data;
      if (format === "csv") {
        // Parse CSV data
        data = Papa.parse(e.target.result, { header: true }).data;
      } else if (format === "xlsx" || format === "xls") {
        // Parse Excel data
        const workbook = XLSX.read(e.target.result, { type: "binary" });
        const sheetName = workbook.SheetNames[0];
        data = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {
          header: 1,
        });
      } else if (format === "geojson") {
        // Parse JSON data
        data = JSON.parse(e.target.result);
      }

      if (data) {
        // Now we have the formatted data
        // Send it to the API
        sendDataToAPI(data, file_name, format, file);
      } else {
        alert("Invalid file format or file is empty.");
      }
    };

    if (file) {
      reader.readAsText(file);
    } else {
      alert("No file selected.");
    }
  } catch (error) {
    alert("Invalid file format or file is empty.");
  }
}

function sendDataToAPI(data, file_name, format, file) {
  const csrftoken = getCookie("csrftoken");
  const progressContainer = document.querySelector(".progress");
  const progressBar = document.querySelector(".progress-bar");
  const progressText = document.querySelector("#upload-progress-text");
  const fileInputContainer = document.querySelector("#uploadFile");
  const downloadDropdown = document.querySelector("#templateFormat");
  const saveBtn = document.querySelector("#saveBtn");
  const closeBtn = document.querySelector("#closeBtn");

  progressContainer.style.visibility = "visible";

  saveBtn.setAttribute("disabled", true);
  closeBtn.setAttribute("disabled", true);
  downloadDropdown.setAttribute("disabled", true);
  fileInputContainer.setAttribute("disabled", true);

  // add setTimeout which changes progressText every 5 seconds

  const texts = [
    "Processing now... please wait",
    "Still processing... please be patient",
    "Still processing...",
  ];

  let currentIndex = 0;
  let countFirstIndexUsed = 0;

  function updateProgress() {
    // Update text
    progressText.innerText = texts[currentIndex];

    // Update the index for the next cycle
    currentIndex = (currentIndex + 1) % texts.length;
  }

  // Initial call to set the first text and progress state
  updateProgress();

  // Update text and progress every 10 seconds
  const intervalId = setInterval(updateProgress, 10000);

  const formData = new FormData();
  formData.append("file_name", file_name);
  formData.append("format", format);
  formData.append("file", file);

  fetch("/api/farm/add/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrftoken,
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
    body: formData,
  })
    .then((response) => {
      clearInterval(intervalId);
      // Update the progress text
      progressText.innerText = "Finishing up...";
      progressBar.style.width = "100%";

      // Sleep for 2 seconds before checking the response.ok
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(response);
        }, 2000);
      });
    })
    .then((response) => {
      if (!response.ok) {
        if (response.status === 400) {
          document
            .querySelector("#modal-error-container")
            .classList.remove("d-none");

          return response.json().then((errorData) => {
            document.querySelector("#headingOneErrorText").textContent =
              errorData?.errors?.[0];
            document
              .querySelector("#close-error-accordion")
              .addEventListener("click", (e) => {
                e.preventDefault();

                document
                  .querySelector("#modal-error-container")
                  .classList.add("d-none");
              });
          });
        }
        throw new Error("Network response was not ok.");
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        Toastify({
          text: "Data were processed successfully!!!",
          duration: 3000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "green",
        }).showToast();

        setTimeout(function () {
          window.location.href = `/validator/?file-id=${data.file_id}`;
        }, 2000);
      }

      saveBtn.removeAttribute("disabled");
      closeBtn.removeAttribute("disabled");
      fileInputContainer.removeAttribute("disabled");
      downloadDropdown.removeAttribute("disabled");
      progressContainer.style.visibility = "hidden";
    })
    .catch((error) => {
      document
        .querySelector("#modal-error-container")
        .classList.remove("d-none");

      document.querySelector("#headingOneErrorText").textContent =
        "Error while uploading data. please try again";
      document
        .querySelector("#close-error-accordion")
        .addEventListener("click", (e) => {
          e.preventDefault();

          document
            .querySelector("#modal-error-container")
            .classList.add("d-none");
        });

      saveBtn.removeAttribute("disabled");
      closeBtn.removeAttribute("disabled");
      fileInputContainer.removeAttribute("disabled");
      downloadDropdown.removeAttribute("disabled");
      progressContainer.style.visibility = "hidden";
    });
}

let dropArea = document.getElementById("drop-area");

["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  dropArea?.addEventListener(eventName, preventDefaults, false);
  document.body.addEventListener(eventName, preventDefaults, false);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropArea?.addEventListener(eventName, highlight, false);
});

["dragleave", "drop"].forEach((eventName) => {
  dropArea?.addEventListener(eventName, unhighlight, false);
});

dropArea?.addEventListener("drop", handleDrop, false);

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight(e) {
  dropArea.classList.add("highlight");
}

function unhighlight(e) {
  dropArea.classList.remove("highlight");
}

function handleDrop(e) {
  let dt = e.dataTransfer;
  let files = dt.files;
  handleFiles(files);
}

function handleFiles(files) {
  [...files].forEach(uploadFile);
}

function uploadFile(file) {
  console.log("Uploading...");
}

dropArea?.addEventListener("click", () => {
  fileElem.click();
});

let fileElem = document.getElementById("fileElem");
fileElem?.addEventListener("change", function (e) {
  handleFiles(this.files);
});

const farmsListTitle = document.getElementById("farms_list_title");
const farmsContainer = document.getElementById("farmsBodyContainer");
const fileId = new URLSearchParams(window.location.search).get("file-id");
const userId = new URLSearchParams(window.location.search).get("user-id");
const collectionSiteDropdown = document.querySelector("#csFilterDropdown");
let farmData = [];
let filteredFarms = [];

const ctx = document.getElementById("plotsPieChart");
let myPieChart = null;

if (ctx) {
  ctx.height = 200;

  myPieChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["High Risk", "Low Risk", "More Info Needed"],
      datasets: [
        {
          data: [0, 0, 0],
          backgroundColor: ["#F64468", "#3AD190", "#ACDCE8"],
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "top",
        },
        tooltip: {
          enabled: true,
        },
        datalabels: {
          color: "#111",
          font: {
            weight: "bold",
            size: 16,
          },
          formatter: (value, context) => {
            return "Fetching plots...";
          },
        },
      },
    },
    plugins: [ChartDataLabels],
  });
}

const colorClasses = {
  low: "low",
  medium: "medium",
  high: "high",
};

let response = null;
if (fileId) {
  response = fetch(`/api/farm/list/file/${fileId}/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
  });
} else {
  response = userId
    ? fetch(`/api/farm/list/user/${userId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
        },
      })
    : fetch("/api/farm/list/", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
        },
      });
}

if (response) {
  response
    .then((resp) => {
      if (!resp.ok) {
        throw new Error("Network response was not ok");
      }
      return resp.json();
    })
    .then((data) => {
      farmData = data;
      filteredFarms = data.map((farm) => {
        farm.updated_at = new Date(farm.updated_at).toLocaleString();
        return farm;
      });
      // order filteredFarms by analysis.eudr_risk_level
      filteredFarms.sort((a, b) => {
        if (a.analysis.eudr_risk_level === "low") {
          return -1;
        } else if (a.analysis.eudr_risk_level === "medium") {
          return 0;
        } else {
          return 1;
        }
      });

      if (document.querySelector("#total_farms")) {
        document.querySelector("#total_farms").innerText = data.length;
        // check where eudr_risk_level is high and calculate the percentage
        const lowRiskFarms = data.filter(
          (farm) => farm.analysis.eudr_risk_level === "low"
        );
        const highRiskFarms = data.filter(
          (farm) => farm.analysis.eudr_risk_level === "high"
        );
        const moreInfoNeededFarms = data.filter(
          (farm) => farm.analysis.eudr_risk_level === "more_info_needed"
        );

        const lowPercentage = (
          (lowRiskFarms.length / data.length) *
          100
        ).toFixed(2);
        const highPercentage = (
          (highRiskFarms.length / data.length) *
          100
        ).toFixed(2);
        const moreInfoNeededPercentage = (
          (moreInfoNeededFarms.length / data.length) *
          100
        ).toFixed(2);

        document.querySelector("#low_farms_rate").innerText = `${
          Number(lowPercentage) || "-"
        }%`;

        if (
          Number(lowPercentage) > 0 ||
          Number(highPercentage) > 0 ||
          Number(moreInfoNeededPercentage) > 0
        ) {
          document
            .querySelector("#pieChartContainer")
            .classList.remove("d-none");
          // update the pie chart
          myPieChart.destroy();
          myPieChart = new Chart(ctx, {
            type: "doughnut",
            data: {
              labels: ["High Risk", "Low Risk", "More Info Needed"],
              datasets: [
                {
                  data: [
                    !isNaN(Number(highPercentage)) ? Number(highPercentage) : 0,
                    !isNaN(Number(lowPercentage)) ? Number(lowPercentage) : 0,
                    !isNaN(Number(moreInfoNeededPercentage))
                      ? Number(moreInfoNeededPercentage)
                      : 0,
                  ],
                  backgroundColor: ["#F64468", "#3AD190", "#ACDCE8"],
                  hoverOffset: 4,
                },
              ],
            },
            options: {
              responsive: true,
              plugins: {
                legend: {
                  position: "top",
                },
                tooltip: {
                  enabled: true,
                },
                datalabels: {
                  color: "#fff",
                  font: {
                    weight: "bold",
                    size: 16,
                  },
                  formatter: (value, context) => {
                    return value + "%";
                  },
                },
              },
            },
            plugins: [ChartDataLabels],
          });
        }
      }
      if (farmsContainer) {
        const cs =
          farmData.find((item) => item.file_id === fileId)?.collection_site ||
          "";
        if (data.length > 0) {
          document
            .querySelector("#exportFormatButton")
            .removeAttribute("disabled");
          // get unique collection sites and populate the dropdown
          const collectionSites = [
            ...new Set(data.map((farm) => farm.collection_site)),
          ];
          collectionSites.forEach((site) => {
            const option = document.createElement("option");
            option.value = site;
            option.innerText = site;
            collectionSiteDropdown.appendChild(option);
          });

          if (cs !== "") {
            document.querySelector("#viewMapBtn").classList.remove("d-none");
            document.querySelector("#viewMapBtn").href += `?file-id=${fileId}`;
            farmsListTitle.innerHTML = `Plots List for ${cs} <i class="fa fa-close bg bg-light p-1 ms-2 rounded-1 cursor-pointer" onclick="window.location.href = '/validator/'"></i>`;
            document.querySelector(
              '#csFilterDropdown [value="' + cs + '"]'
            ).selected = true;

            document
              .querySelector("#revalidate-all")
              .classList.remove("d-none");

            document
              .querySelector("#revalidate-all")
              .addEventListener("click", () => {
                // open fullpageLoaderModal
                const fullpageLoaderModal = new bootstrap.Modal(
                  document.getElementById("fullpageLoaderModal"),
                  {
                    backdrop: "static",
                    keyboard: false,
                  }
                );
                fullpageLoaderModal.show();
                fetch(`/api/farm/revalidate/${fileId}/`, {
                  method: "GET",
                  headers: {
                    "Content-Type": "application/json",
                    Authorization: `Token ${localStorage.getItem(
                      "terratracAuthToken"
                    )}`,
                  },
                })
                  .then((resp) => {
                    if (!resp.ok) {
                      // close fullpageLoaderModal
                      fullpageLoaderModal.hide();
                      throw new Error("Network response was not ok");
                    }
                    return resp.json();
                  })
                  .then((data) => {
                    // close fullpageLoaderModal
                    fullpageLoaderModal.hide();
                    if (data) {
                      Toastify({
                        text: "All plots revalidated successfully!!!",
                        duration: 3000,
                        close: true,
                        gravity: "top",
                        position: "right",
                        backgroundColor: "green",
                      }).showToast();

                      setTimeout(function () {
                        window.location.reload();
                      }, 2000);
                    }
                  })
                  .catch((error) => {
                    // close fullpageLoaderModal
                    fullpageLoaderModal.hide();
                    Toastify({
                      text: "Error while revalidating plots. please try again",
                      duration: 3000,
                      close: true,
                      gravity: "top",
                      position: "right",
                      backgroundColor: "red",
                    }).showToast();
                  });
              });

            checkOverLappingFarms(fileId);
          }
        }

        // remove loading spinner
        farmsContainer.innerHTML = "";

        generateData(data, farmsContainer);
      }
    })
    .catch((error) => {
      console.error("There was a problem with the fetch operation:", error);
    });
}

function checkOverLappingFarms(fileId) {
  fetch(`/api/farm/overlapping/${fileId}/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
  })
    .then((resp) => {
      if (!resp.ok) {
        throw new Error("Network response was not ok");
      }
      return resp.json();
    })
    .then((data) => {
      if (data.length > 0) {
        document.querySelector("#viewOverlapsBtn").classList.remove("d-none");

        document.querySelector(
          "#viewOverlapsBtn"
        ).href += `?file-id=${fileId}&overlaps=true`;
      }
    })
    .catch((error) => {
      console.error("There was a problem with the fetch operation:", error);
    });
}

function viewAnalysis(id) {
  const container = document.getElementById("whispCardsContainer");
  container.innerHTML = "";

  const obj = farmData.find((farm) => farm.id === id);

  Object.keys(obj?.analysis).forEach((key) => {
    const value = obj.analysis[key];

    const card = document.createElement("div");
    card.className = "whisp-item-card";
    card.innerHTML = `
                <h6>${key
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, (char) => char.toUpperCase())}</h6>
                <p class="${
                  key === "eudr_risk_level" && value === "high"
                    ? "bg-gradient rounded-1 px-2 text-white"
                    : value === "more_info_needed"
                    ? "bg-gradient rounded-1 px-2 text-white"
                    : value === "low"
                    ? "bg-gradient rounded-1 px-2 text-white"
                    : value
                }" style="background-color: ${
      value === "high"
        ? "#FF1C49"
        : value === "more_info_needed"
        ? "#78DBF4"
        : value === "low"
        ? "#15E289"
        : value
    }">${
      !isNaN(value) && value > 0
        ? `${value} ha`
        : key === "eudr_risk_level"
        ? value
            .replace(/_/g, " ")
            .replace(/\b\w/g, (char) => char.toUpperCase()) || "-"
        : typeof value === "string"
        ? value
            .replace(/_/g, " ")
            .replace(/\b\w/g, (char) => char.toUpperCase()) || "-"
        : value === null || value === "-"
        ? "No"
        : value
    }</p>
        `;
    container.appendChild(card);
  });

  const whispDataModal = new bootstrap.Modal(
    document.getElementById("whispAnalysisModal"),
    {
      backdrop: "static",
      keyboard: false,
    }
  );

  whispDataModal.show();
}

// filter farms by collection site, if all sites are selected, show all farms, otherwise, show farms for the selected site
collectionSiteDropdown?.addEventListener("change", (e) => {
  $("#farms").DataTable().destroy();
  const selectedSite = e.target.value;
  filteredFarms =
    selectedSite === ""
      ? farmData
      : farmData.filter((farm) => farm.collection_site === selectedSite);

  farmsContainer.innerHTML = "";

  generateData(filteredFarms, farmsContainer);
});

// filter farms by eudr_risk_level
document
  .querySelector("#riskLevelFilterDropdown")
  ?.addEventListener("change", (e) => {
    $("#farms").DataTable().destroy();
    const selectedRiskLevel = e.target.value;
    filteredFarms =
      selectedRiskLevel === ""
        ? farmData
        : farmData.filter(
            (farm) => farm.analysis.eudr_risk_level === selectedRiskLevel
          );

    farmsContainer.innerHTML = "";

    generateData(filteredFarms, farmsContainer);
  });

async function handleExport(format) {
  const languageCode = localStorage.getItem("terraTracLang") || "en";
  const columns = await loadJsonFile(languageCode);
  const file_names = {
    en: "validated_farms",
    fr: "fermes_validées",
    rw: "ubutaka_bwasuzumwe",
    es: "granjas_validadas",
    sw: "mashamba_yaliyothibitishwa",
  };

  switch (format) {
    case "xls":
      exportToExcel(columns, file_names[languageCode]);
      break;
    case "geojson":
      exportToGeoJSON(columns, file_names[languageCode]);
      break;
    case "pdf":
      exportToPDF(columns, file_names[languageCode]);
      break;
    default:
      break;
  }
}

async function exportToExcel(columns, file_name) {
  const data = filteredFarms.map((farm) => {
    const farmData = {};
    Object.keys(columns).forEach((column) => {
      if (column === "analysis") {
        Object.keys(columns[column]).forEach((col) => {
          farmData[columns[column][col]] = farm[column][col];
        });
      } else {
        farmData[columns[column]] = farm[column];
      }
    });
    return farmData;
  });

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Plots Data");

  // Add headers and apply bold styling
  const headers = Object.keys(data[0]);
  const headerRow = worksheet.addRow(headers);

  // Apply bold formatting to the headers
  headerRow.eachCell((cell) => {
    cell.font = { bold: true };
  });

  // Add data starting from the 2nd row
  data.forEach((farmData) => {
    worksheet.addRow(Object.values(farmData));
  });

  // Save file
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${file_name}_${new Date().toISOString()}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function exportToGeoJSON(columns, file_name) {
  let properties = {};
  const features = filteredFarms.map((farm) => {
    properties = {};

    // Iterate over the columns
    Object.keys(columns).forEach((column) => {
      // Check if the column is "analysis"
      if (column === "analysis") {
        properties[column] = {};
        // Iterate over the keys in the "analysis" column
        Object.keys(columns[column]).forEach((col) => {
          // Assign the values from the farm object to the properties object
          properties[columns[column][col]] = farm[column][col];
        });
      } else {
        // Directly assign the values for other columns
        properties[columns[column]] = farm[column];
      }
    });
    return {
      type: "Feature",
      properties,
      geometry: {
        type: farm.polygon ? "Polygon" : "Point",
        coordinates: farm.polygon
          ? farm.polygon
          : [farm.longitude, farm.latitude],
      },
    };
  });

  const geoJSON = {
    type: "FeatureCollection",
    features: features,
  };

  const blob = new Blob([JSON.stringify(geoJSON)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${file_name}_${new Date().toISOString()}.geojson`;
  a.click();
}

function exportToPDF(columns, file_name) {
  const doc = new jsPDF({
    orientation: "landscape",
    format: "a2",
  });
  const pageWidth = doc.internal.pageSize.getWidth();
  const image = new Image();
  image.src = "/static/assets/img/tns-logo-png.png";
  doc.addImage(image, "PNG", pageWidth / 2, 10, 20, 20);

  // Add the title
  const title = "Validated Plots";
  doc.setFontSize(18); // Set font size
  const textWidth = doc.getTextWidth(title);
  const x = pageWidth / 2; // Center the text
  doc.text(title, x, 40); // Adjust the y position as needed

  // Define table configuration
  const maxWidth = pageWidth; // Page width minus margins
  let fontSize = 13; // Starting font size

  // Function to adjust column widths
  function getColumnWidths(columns, tableWidth) {
    const totalColumns = columns.length;
    const columnWidth = tableWidth / totalColumns;
    return Array(totalColumns).fill(columnWidth);
  }

  // Get column widths
  let columnWidths = getColumnWidths(
    Object.keys(columns)
      .map((column) =>
        column === "analysis"
          ? Object.keys(columns[column]).map((col) => columns[column][col])
          : columns[column]
      )
      .flat(1),
    maxWidth
  );

  // Add table
  doc.autoTable({
    startY: 50,
    columns: [
      ...Object.keys(columns)
        .map((column) =>
          column === "analysis"
            ? Object.keys(columns[column]).map((col) => columns[column][col])
            : columns[column]
        )
        .flat(1),
    ].map((header, index) => ({
      header,
      width: columnWidths[index] || 40, // Default width if undefined
    })),
    body: [
      ...filteredFarms.map((farm) => {
        const farmData = [];
        Object.keys(columns).forEach((column) => {
          if (column === "analysis") {
            Object.keys(columns[column]).forEach((col) => {
              farmData.push(farm[column][col]);
            });
          } else {
            farmData.push(farm[column]);
          }
        });
        return farmData;
      }),
    ],
    styles: {
      cellWidth: "wrap",
      minCellHeight: 10,
      fontSize: fontSize, // Use the initial font size
    },
    margin: { top: 10 },
    columnStyles: {
      0: { cellWidth: "auto" }, // Adjust as needed
    },
    headStyles: {
      fontSize: fontSize - 2,
      cellWidth: "10px",
    },
    bodyStyles: {
      fontSize: fontSize - 2,
      cellWidth: "wrap",
    },
    didDrawPage: (data) => {
      // Adjust column widths if necessary
      const tableWidth = data.table.width;
      if (tableWidth > maxWidth) {
        fontSize = Math.max(fontSize - 1, 6); // Reduce font size
        columnWidths = getColumnWidths(
          Object.keys(columns)
            .map((column) =>
              column === "analysis"
                ? Object.keys(columns[column]).map(
                    (col) => columns[column][col]
                  )
                : columns[column]
            )
            .flat(1),
          maxWidth
        );
        doc.autoTable({
          ...data.table,
          styles: { fontSize },
          columnStyles: columnWidths.reduce((acc, width, index) => {
            acc[index] = { cellWidth: width };
            return acc;
          }, {}),
        });
      }
    },
    pageBreak: "auto", // Automatically break the table into pages if necessary
  });

  doc.save(`${file_name}_${new Date().toISOString()}.pdf`);
}

async function loadJsonFile(languageCode) {
  return await fetch("/static/assets/json/exportable_columns.json", {
    cache: "no-cache",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => data[languageCode] || data["en"])
    .catch((error) => error);
}

function generateData(farmData, farmsContainer) {
  let i = 0;
  while (i < farmData.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
            <td></td>
            <td>
              <p class="text-xs text-center font-weight-bold mb-0">${i + 1}.</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0 geoid-sel">${
                farmData[i].geoid || "N/A"
              }</p>
            </td>
            <td>
              <div class="d-flex px-2 py-1">
                <div class="d-flex flex-column justify-content-center">
                  <h6 class="mb-0 text-sm">${farmData[i].farmer_name}</h6>
                </div>
              </div>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                farmData[i].farm_size
              }</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                farmData[i].collection_site
              }</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                farmData[i].farm_village
              }</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                farmData[i].farm_district
              }</p>
            </td>
            <td>
              <p
                class="${
                  farmData[i].analysis.eudr_risk_level === "high"
                    ? "text-xs font-weight-bold mb-0"
                    : farmData[i].analysis.eudr_risk_level ===
                      "more_info_needed"
                    ? "text-xs font-weight-bold mb-0"
                    : farmData[i].analysis.eudr_risk_level === "low"
                    ? "text-xs font-weight-bold mb-0"
                    : farmData[i].analysis.eudr_risk_level
                }" style="color: ${
      farmData[i].analysis.eudr_risk_level === "high"
        ? "#FF1C49"
        : farmData[i].analysis.eudr_risk_level === "more_info_needed"
        ? "#78DBF4"
        : farmData[i].analysis.eudr_risk_level === "low"
        ? "#15E289"
        : farmData[i].analysis.eudr_risk_level
    }">${
      farmData[i].analysis.eudr_risk_level
        .replace(/_/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase()) || "-"
    }</p>
            </td>
            <td class="align-middle text-center text-sm">
              <i class="bi bi-eye mt-5 text-primary text-lg" data-toggle="modal" data-target="#whispDataModal"
                id="viewAnalysisBtn" role="button" onclick="viewAnalysis(${
                  farmData[i].id
                })" title="View Analysis"></i>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${new Date(
                farmData[i].updated_at
              ).toDateString()}</p>
            </td>
            <td class="align-middle text-center">
              <a href="${mapUrl}?farm-id=${
      farmData[i].id
    }" class="text-primary font-weight-bold text-lg" title="View on Map"><i class="bi bi-cursor"></i></a>
            </td>
        `;
    farmsContainer.appendChild(tr);
    i++;
  }

  const tableCustoms = $("#farms").DataTable({
    // add loading spinner while table is being loaded
    processing: true,
    //disable sorting on last column
    columnDefs: [
      {
        targets: 0,
        className: "dt-control",
        orderable: false,
        data: null,
        defaultContent: "",
      },
      {
        targets: [4, 5, 6, 7],
        visible: false,
      },
    ],
    order: [[1, "asc"]],
    language: {
      //customize pagination prev and next buttons: use arrows instead of words
      paginate: {
        previous: '<span class="fa fa-chevron-left"></span>',
        next: '<span class="fa fa-chevron-right"></span>',
      },
      //customize number of elements to be displayed
      lengthMenu:
        'Display <select class="form-control input-sm">' +
        '<option value="10">10</option>' +
        '<option value="20">20</option>' +
        '<option value="30">30</option>' +
        '<option value="40">40</option>' +
        '<option value="50">50</option>' +
        '<option value="-1">All</option>' +
        "</select> results",
    },
  });

  function format(rowData) {
    return `
        <div class="accordion-content">
            <div><b>Farm Size (Ha):</b> ${rowData[4]}</div>
            <div><b>Site Name:</b> ${rowData[5]}</div>
            <div><b>Village:</b> ${rowData[6]}</div>
            <div><b>District:</b> ${rowData[7]}</div>
        </div>`;
  }

  $("#farms tbody").on("click", "td.dt-control", function () {
    const tr = $(this).closest("tr");
    const row = tableCustoms.row(tr);

    if (row.child.isShown()) {
      // Close the accordion
      row.child.hide();
      tr.removeClass("shown");
    } else {
      // Open the accordion
      row.child(format(row.data())).show();
      tr.addClass("shown");
    }
  });
}

const filesContainer = document.getElementById("filesContainer");

fetch("/api/files/list/", {
  method: "GET",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
  },
})
  .then((response) => {
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return response.json();
  })
  .then((data) => {
    let i = 0;

    if (document.querySelector("#total_files_uploaded")) {
      document.querySelector("#total_files_uploaded").innerText = data.length;
    }

    if (filesContainer) {
      // remove loading spinner
      filesContainer.innerHTML = "";

      while (i < data.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
                  <td>
                    <p class="text-xs font-weight-bold px-3 mb-0">${i + 1}.</p>
                  </td>
                  <td>
                    <div class="d-flex px-2 py-1">
                      <div class="d-flex justify-content-center align-items-center gap-2">
                        <span class="fa fa-file-alt text-primary text-xs"></span>
                        <h6 class="mb-0 text-sm">${data[i].file_name}</h6>
                      </div>
                    </div>
                  </td>
                  <td>
                    <p class="text-xs font-weight-bold mb-0">${
                      data[i].uploaded_by
                    }</p>
                  </td>
                  <td>
                    <p class="text-xs font-weight-bold mb-0">${new Date(
                      data[i].updated_at
                    ).toLocaleString()}</p>
                  </td>
                  <td>
                    <a
                      href="${validatorUrl}?file-id=${data[i].id}"
                      class="text-primary font-weight-bold text-lg me-3"
                      title="View List of Plots"
                      ><i class="bi bi-list"></i></a
                    >
                    <a
                      href="${mapUrl}?file-id=${data[i].id}"
                      class="text-primary font-weight-bold text-lg"
                      title="View on Map"
                      ><i class="bi bi-cursor"></i></a
                    >
                  </td>
              `;

        filesContainer.appendChild(tr);
        i++;
      }

      $("#files").DataTable({
        language: {
          //customize pagination prev and next buttons: use arrows instead of words
          paginate: {
            previous: '<span class="fa fa-chevron-left"></span>',
            next: '<span class="fa fa-chevron-right"></span>',
          },
          //customize number of elements to be displayed
          lengthMenu:
            'Display <select class="form-control input-sm">' +
            '<option value="10">10</option>' +
            '<option value="20">20</option>' +
            '<option value="30">30</option>' +
            '<option value="40">40</option>' +
            '<option value="50">50</option>' +
            '<option value="-1">All</option>' +
            "</select> results",
        },
      });
    }
  })
  .catch((error) => {
    console.error("There was a problem with the fetch operation:", error);
  });

const allFilesContainer = document.getElementById("allFilesContainer");

fetch("/api/files/list/all/", {
  method: "GET",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
  },
})
  .then((response) => {
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return response.json();
  })
  .then((data) => {
    let i = 0;

    if (document.querySelector("#all_files_uploaded")) {
      document.querySelector("#all_files_uploaded").innerText = data.length;
    }

    if (allFilesContainer) {
      // remove loading spinner
      allFilesContainer.innerHTML = "";

      while (i < data.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
              <td>
                <p class="text-xs font-weight-bold px-3 mb-0">${i + 1}.</p>
              </td>
              <td>
                <div class="d-flex px-2 py-1">
                  <div class="d-flex justify-content-center align-items-center gap-2">
                    <span class="fa fa-file-alt text-primary text-xs"></span>
                    <h6 class="mb-0 text-sm">${data[i].file_name}</h6>
                  </div>
                </div>
              </td>
              <td>
                    <p class="mb-0 text-sm">${Number(data[i].size).toFixed(
                      1
                    )}Kbs</p>
              </td>
              <td>
                <p class="text-xs font-weight-bold mb-0">${
                  data[i].uploaded_by
                }</p>
              </td>
              <td>
                <p class="btn btn-${
                  data[i].category === "processed" ? "success" : "danger"
                } text-xs font-weight-bold mb-0">${data[
          i
        ].category.toUpperCase()}</p>
              </td>
              <td>
                <p class="text-xs font-weight-bold mb-0">${new Date(
                  data[i].last_modified
                ).toLocaleString()}</p>
              </td>
              <td>
                <a
                  href="${data[i].url}"
                  class="text-primary font-weight-bold text-lg me-3"
                  title="Download File"
                  download
                  ><i class="bi bi-download"></i></a
                >
              </td>
          `;

        allFilesContainer.appendChild(tr);
        i++;
      }

      $("#all_files").DataTable({
        language: {
          //customize pagination prev and next buttons: use arrows instead of words
          paginate: {
            previous: '<span class="fa fa-chevron-left"></span>',
            next: '<span class="fa fa-chevron-right"></span>',
          },
          //customize number of elements to be displayed
          lengthMenu:
            'Display <select class="form-control input-sm">' +
            '<option value="10">10</option>' +
            '<option value="20">20</option>' +
            '<option value="30">30</option>' +
            '<option value="40">40</option>' +
            '<option value="50">50</option>' +
            '<option value="-1">All</option>' +
            "</select> results",
        },
      });
    }
  })
  .catch((error) => {
    console.error("There was a problem with the fetch operation:", error);
  });

const usersContainer = document.getElementById("usersContainer");

if (document.querySelector("#total_users") || usersContainer) {
  fetch("/api/users/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      let i = 0;

      if (document.querySelector("#total_users")) {
        document.querySelector("#total_users").innerText = data.length;
      }

      if (usersContainer) {
        // remove loading spinner
        usersContainer.innerHTML = "";

        while (i < data.length) {
          const tr = document.createElement("tr");
          tr.innerHTML = `
              <td>
                <p class="text-xs font-weight-bold px-3 mb-0">${i + 1}.</p>
              </td>
              <td>
                  <h6 class="mb-0 text-sm">${data[i].first_name} ${
            data[i].last_name
          }</h6>
              </td>
              <td>
                <p class="text-xs font-weight-bold mb-0">${data[i].username}</p>
              </td>
              <td>
                <p class="text-xs font-weight-bold mb-0">${
                  data[i].is_active ? "Active" : "Inactive"
                }</p>
              </td>
              <td>
                <p class="text-xs font-weight-bold mb-0">${new Date(
                  data[i].date_joined
                ).toLocaleString()}</p>
              </td>
              <td class="d-flex justify-content-center gap-3">
                <a
                  href="${validatorUrl}?user-id=${data[i].id}"
                  class="text-primary font-weight-bold text-lg"
                  title="View User List of Plots"
                  ><i class="bi bi-list"></i></a
                >
                ${
                  data[i].is_superuser
                    ? ""
                    : `<a
                  href="#?user-id=${data[i].id}"
                  class="text-primary font-weight-bold text-lg"
                  title="Edit User"
                  ><i class="bi bi-pen"></i></a
                >
                <a
                  href="#?user-id=${data[i].id}"
                  class="text-primary font-weight-bold text-lg"
                  title="Delete User"
                  ><i class="bi bi-trash"></i></a
                >`
                }
              </td>
          `;

          usersContainer.appendChild(tr);
          i++;
        }

        $("#users").DataTable({
          language: {
            //customize pagination prev and next buttons: use arrows instead of words
            paginate: {
              previous: '<span class="fa fa-chevron-left"></span>',
              next: '<span class="fa fa-chevron-right"></span>',
            },
            //customize number of elements to be displayed
            lengthMenu:
              'Display <select class="form-control input-sm">' +
              '<option value="10">10</option>' +
              '<option value="20">20</option>' +
              '<option value="30">30</option>' +
              '<option value="40">40</option>' +
              '<option value="50">50</option>' +
              '<option value="-1">All</option>' +
              "</select> results",
          },
        });
      }
    })
    .catch((error) => {
      console.error(
        "There was a problem with the fetch users operation:",
        error
      );
    });
}

const backupsContainer = document.getElementById("backupsContainer");

fetch("/api/collection_sites/list", {
  method: "GET",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
  },
})
  .then((response) => {
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return response.json();
  })
  .then((data) => {
    let i = 0;

    if (document.querySelector("#total_backups")) {
      document.querySelector("#total_backups").innerText = data.length;
    }

    if (backupsContainer) {
      // remove loading spinner
      backupsContainer.innerHTML = "";

      while (i < data.length) {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td></td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${data[i].device_id}</p>
            </td>
            <td>
              <h6 class="mb-0 text-sm">${data[i].name}</h6>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${data[i].agent_name}</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                data[i].email || "N/A"
              }</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${
                data[i].phone_number || "N/A"
              }</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${data[i].village}</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${data[i].district}</p>
            </td>
            <td>
              <p class="text-xs font-weight-bold mb-0">${new Date(
                data[i].updated_at
              ).toLocaleString()}</p>
            </td>
            <td class="align-middle text-center">
              <a href="${backupDetailsUrl}?cs-id=${
          data[i].id
        }" class="text-primary font-weight-bold text-lg" title="View Details"><i class="bi bi-list"></i></a>
            </td>
      `;

        backupsContainer.appendChild(tr);
        i++;
      }

      const tableCustoms = $("#backups").DataTable({
        columnDefs: [
          {
            targets: 0,
            className: "dt-control",
            orderable: false,
            data: null,
            defaultContent: "",
          },
          {
            targets: [2, 3, 4, 5, 6, 7],
            visible: false,
          },
        ],
        order: [[1, "asc"]],
        language: {
          //customize pagination prev and next buttons: use arrows instead of words
          paginate: {
            previous: '<span class="fa fa-chevron-left"></span>',
            next: '<span class="fa fa-chevron-right"></span>',
          },
          //customize number of elements to be displayed
          lengthMenu:
            'Display <select class="form-control input-sm">' +
            '<option value="10">10</option>' +
            '<option value="20">20</option>' +
            '<option value="30">30</option>' +
            '<option value="40">40</option>' +
            '<option value="50">50</option>' +
            '<option value="-1">All</option>' +
            "</select> results",
        },
      });

      function format(rowData) {
        return `
            <div class="accordion-content">
                <div><b>Site Name:</b> ${rowData[2]}</div>
                <div><b>Agent Name:</b> ${rowData[3]}</div>
                <div><b>Email:</b> ${rowData[4]}</div>
                <div><b>Phone Number:</b> ${rowData[5]}</div>
                <div><b>Village:</b> ${rowData[6]}</div>
                <div><b>District:</b> ${rowData[7]}</div>
            </div>`;
      }

      $("#backups tbody").on("click", "td.dt-control", function () {
        const tr = $(this).closest("tr");
        const row = tableCustoms.row(tr);

        if (row.child.isShown()) {
          // Close the accordion
          row.child.hide();
          tr.removeClass("shown");
        } else {
          // Open the accordion
          row.child(format(row.data())).show();
          tr.addClass("shown");
        }
      });
    }
  })
  .catch((error) => {
    console.error(
      "There was a problem with the fetch backups operation:",
      error
    );
  });

const backupDetailsContainer = document.getElementById(
  "backupDetailsContainer"
);
const queryParams = new URLSearchParams(window.location.search);

if (queryParams.get("cs-id")) {
  fetch(`/api/farm/sync/list/${queryParams.get("cs-id")}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      let i = 0;

      if (backupDetailsContainer) {
        // remove loading spinner
        backupDetailsContainer.innerHTML = "";

        while (i < data.length) {
          const tr = document.createElement("tr");

          tr.innerHTML = `
                <td></td>
                <td>
                  <p class="text-xs font-weight-bold px-3 mb-0">${i + 1}.</p>
                </td>
                <td>
                  <h6 class="mb-0 text-sm">${data[i].remote_id}</h6>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].farmer_name
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].member_id
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${data[i].size}</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].village
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].district
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].latitude
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].longitude
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${
                    data[i].coordinates ? "Yes" : "No"
                  }</p>
                </td>
                <td>
                  <p class="text-xs font-weight-bold mb-0">${new Date(
                    data[i].updated_at
                  ).toLocaleString()}</p>
                </td>
  `;

          backupDetailsContainer.appendChild(tr);
          i++;
        }

        const tableCustoms = $("#backup_details").DataTable({
          columnDefs: [
            {
              targets: 0,
              className: "dt-control",
              orderable: false,
              data: null,
              defaultContent: "",
            },
            {
              targets: [6, 7, 8, 9, 10],
              visible: false,
            },
          ],
          order: [[1, "asc"]],
          language: {
            //customize pagination prev and next buttons: use arrows instead of words
            paginate: {
              previous: '<span class="fa fa-chevron-left"></span>',
              next: '<span class="fa fa-chevron-right"></span>',
            },
            //customize number of elements to be displayed
            lengthMenu:
              'Display <select class="form-control input-sm">' +
              '<option value="10">10</option>' +
              '<option value="20">20</option>' +
              '<option value="30">30</option>' +
              '<option value="40">40</option>' +
              '<option value="50">50</option>' +
              '<option value="-1">All</option>' +
              "</select> results",
          },
        });

        function format(rowData) {
          console.log(rowData);
          return `
              <div class="accordion-content">
                  <div><b>Village:</b> ${rowData[6]}</div>
                  <div><b>District:</b> ${rowData[7]}</div>
                  <div><b>Latitude:</b> ${rowData[8]}</div>
                  <div><b>Longitude:</b> ${rowData[9]}</div>
                  <div><b>Has Polygon:</b> ${rowData[10] ? "Yes" : "No"}</div>
              </div>`;
        }

        $("#backup_details tbody").on("click", "td.dt-control", function () {
          const tr = $(this).closest("tr");
          const row = tableCustoms.row(tr);

          if (row.child.isShown()) {
            // Close the accordion
            row.child.hide();
            tr.removeClass("shown");
          } else {
            // Open the accordion
            row.child(format(row.data())).show();
            tr.addClass("shown");
          }
        });
      }
    })
    .catch((error) => {
      console.error(
        "There was a problem with the fetch backups operation:",
        error
      );
    });
}

if (window.location.pathname === "/map/") {
  $("#loader-container").show();

  const queryParams = new URLSearchParams(window.location.search);
  const fileId = queryParams.get("file-id");
  const farmId = queryParams.get("farm-id");
  const lat = queryParams.get("lat");
  const lon = queryParams.get("lon");

  $.ajax({
    url: mapViewUrl,
    dataType: "json",
    data: {
      "file-id": fileId,
      "farm-id": farmId,
      lat: lat,
      lon: lon,
    },
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
    success: function (data) {
      if (data.error) {
        Toastify({
          text: data.error,
          duration: 3000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "red",
        }).showToast();
      } else {
        $("#mapMonde").html(data.map_html);
        document.querySelector(".floating-share").classList.remove("d-none");
      }
      $("#loader-container").hide();
    },
    error: function () {
      Toastify({
        text: "Error loading map data.",
        duration: 3000,
        close: true,
        gravity: "top",
        position: "right",
        backgroundColor: "red",
      }).showToast();
      $("#loader-container").hide();
    },
  });
}

// Share map logic
if (document.querySelector(".floating-share .fa-share-alt")) {
  document
    .querySelector(".floating-share .fa-share-alt")
    .addEventListener("click", function () {
      document.querySelector(".share-options").classList.toggle("show");
    });

  document
    .getElementById("copyLink")
    .addEventListener("click", async function (e) {
      e.preventDefault();
      const queryParams = new URLSearchParams(window.location.search);
      const fileId = queryParams.get("file-id");

      const shareUrl = await generateMapUrl(fileId);

      if (shareUrl) {
        navigator.clipboard.writeText(shareUrl).then(() => {
          Toastify({
            text: "Link copied to clipboard!",
            duration: 2000,
            close: true,
            gravity: "top",
            position: "right",
            backgroundColor: "green",
          }).showToast();
        });
      }
    });

  document
    .getElementById("whatsappShare")
    .addEventListener("click", async function (e) {
      e.preventDefault();
      const queryParams = new URLSearchParams(window.location.search);
      const fileId = queryParams.get("file-id");

      const shareUrl = await generateMapUrl(fileId);

      if (shareUrl) {
        window.open(
          `https://wa.me/?text=${encodeURIComponent(shareUrl)}`,
          "_blank"
        );
      }
    });

  document
    .getElementById("emailShare")
    .addEventListener("click", async function (e) {
      e.preventDefault();
      const queryParams = new URLSearchParams(window.location.search);
      const fileId = queryParams.get("file-id");

      const shareUrl = await generateMapUrl(fileId);

      if (shareUrl) {
        window.open(
          `mailto:?subject=Check%20out%20this%20map&body=${encodeURIComponent(
            shareUrl
          )}`,
          "_self"
        );
      }
    });

  async function generateMapUrl(fileId) {
    let shareUrl = null;

    await $.ajax({
      url: mapShareUrl,
      dataType: "json",
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: {
        "file-id": fileId,
      },
      success: function (data) {
        if (data.error) {
          Toastify({
            text: data.error,
            duration: 2000,
            close: true,
            gravity: "top",
            position: "right",
            backgroundColor: "red",
          }).showToast();
        } else {
          shareUrl = data.map_link;
        }
      },
      error: function () {
        Toastify({
          text: "Error generating share link.",
          duration: 2000,
          close: true,
          gravity: "top",
          position: "right",
          backgroundColor: "red",
        }).showToast();
      },
    });

    return shareUrl;
  }
}
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get("open-uploader") === "true") {
  // Use Bootstrap's modal method to show the modal
  var myModal = new bootstrap.Modal(
    document.getElementById("uploadFarmInfoModal"),
    {
      backdrop: "static",
      keyboard: true,
    }
  );
  myModal.show();
}

if (window.location.pathname === "/map/share/") {
  $("#loader-container").show();

  const queryParams = new URLSearchParams(window.location.search);
  const fileId = queryParams.get("file-id");
  const accessCode = queryParams.get("access-code");

  $.ajax({
    url: mapViewUrl,
    dataType: "json",
    data: {
      "file-id": fileId,
      "access-code": accessCode,
    },
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
      Authorization: `Token ${localStorage.getItem("terratracAuthToken")}`,
    },
    success: function (data) {
      if (data.error) {
        $("#error-container").removeClass("d-none");
        $("#error-container .message-subtitle").text(data.error);
      } else if (data?.status === 403) {
        $("#error-container").removeClass("d-none");
        $("#error-container .message-subtitle").text(data.message);
      } else {
        $("#mapMonde").html(data.map_html);
      }
      $("#loader-container").hide();
    },
    error: function (error) {
      $("#loader-container").hide();
      $("#error-container").removeClass("d-none");
      $("#error-container .message-subtitle").text(
        "An error occurred while loading the map"
      );
    },
  });
}
