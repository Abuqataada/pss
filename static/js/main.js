// Main JavaScript file for PSS Investment Platform

document.addEventListener("DOMContentLoaded", () => {
  // Initialize tooltips
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => new window.bootstrap.Tooltip(tooltipTriggerEl))

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert")
  alerts.forEach((alert) => {
    if (alert.classList.contains("alert-success") || alert.classList.contains("alert-info")) {
      setTimeout(() => {
        const bsAlert = new window.bootstrap.Alert(alert)
        bsAlert.close()
      }, 5000)
    }
  })

  // Form validation
  const forms = document.querySelectorAll(".needs-validation")
  forms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault()
        event.stopPropagation()
      }
      form.classList.add("was-validated")
    })
  })

  // Number formatting
  const numberInputs = document.querySelectorAll('input[type="number"]')
  numberInputs.forEach((input) => {
    input.addEventListener("input", function () {
      // Remove any non-numeric characters except decimal point
      this.value = this.value.replace(/[^0-9.]/g, "")
    })
  })

  // Copy to clipboard function
  window.copyToClipboard = (text) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        window.showToast("Copied to clipboard!", "success")
      })
      .catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement("textarea")
        textArea.value = text
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand("copy")
        document.body.removeChild(textArea)
        window.showToast("Copied to clipboard!", "success")
      })
  }

  // Toast notification function
  window.showToast = (message, type = "info") => {
    const toastContainer = document.getElementById("toast-container") || createToastContainer()

    const toast = document.createElement("div")
    toast.className = `toast align-items-center text-white bg-${type} border-0`
    toast.setAttribute("role", "alert")
    toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `

    toastContainer.appendChild(toast)
    const bsToast = new window.bootstrap.Toast(toast)
    bsToast.show()

    // Remove toast element after it's hidden
    toast.addEventListener("hidden.bs.toast", () => {
      toast.remove()
    })
  }

  function createToastContainer() {
    const container = document.createElement("div")
    container.id = "toast-container"
    container.className = "toast-container position-fixed top-0 end-0 p-3"
    container.style.zIndex = "1055"
    document.body.appendChild(container)
    return container
  }

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault()
      const target = document.querySelector(this.getAttribute("href"))
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        })
      }
    })
  })

  // Loading state for buttons
  window.setButtonLoading = (button, loading = true) => {
    if (loading) {
      button.disabled = true
      const originalText = button.innerHTML
      button.setAttribute("data-original-text", originalText)
      button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...'
    } else {
      button.disabled = false
      button.innerHTML = button.getAttribute("data-original-text")
    }
  }

  // Format currency inputs
  const currencyInputs = document.querySelectorAll(".currency-input")
  currencyInputs.forEach((input) => {
    input.addEventListener("input", function () {
      const value = this.value.replace(/[^\d.]/g, "")
      if (value) {
        this.value = Number.parseFloat(value).toLocaleString()
      }
    })
  })

  // Confirm dangerous actions
  const dangerButtons = document.querySelectorAll(".btn-danger[data-confirm]")
  dangerButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      const message = this.getAttribute("data-confirm")
      if (!confirm(message)) {
        e.preventDefault()
        return false
      }
    })
  })
})

// Utility functions
function formatCurrency(amount) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
  }).format(amount)
}

function formatNumber(number) {
  return new Intl.NumberFormat("en-NG").format(number)
}

// Investment calculator
function calculateReturns(principal, months, rate = 0.1) {
  return principal * (1 + rate * months)
}

// Referral code generator (client-side validation)
function validateReferralCode(code) {
  return /^[A-Z0-9]{8}$/.test(code)
}
