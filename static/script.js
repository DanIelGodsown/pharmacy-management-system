// Pharmacy Management System JavaScript

$(document).ready(function() {
    // Auto-update alerts every 30 seconds
    setInterval(updateAlerts, 30000);
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
});

function updateAlerts() {
    $.get('/api/alerts', function(data) {
        let alertsHtml = '';
        
        if (data.low_stock > 0) {
            alertsHtml += `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${data.low_stock} drugs are low in stock
                </div>
            `;
        }
        
        if (data.expiring_soon > 0) {
            alertsHtml += `
                <div class="alert alert-danger">
                    <i class="fas fa-clock"></i>
                    ${data.expiring_soon} drugs are expiring soon
                </div>
            `;
        }
        
        if (data.expired > 0) {
            alertsHtml += `
                <div class="alert alert-dark">
                    <i class="fas fa-skull-crossbones"></i>
                    ${data.expired} drugs have expired
                </div>
            `;
        }
        
        if (alertsHtml === '') {
            alertsHtml = '<div class="alert alert-success"><i class="fas fa-check-circle"></i> No alerts at this time.</div>';
        }
        
        $('#alerts-container').html(alertsHtml);
    });
}

// Drug search functionality
function searchDrugs(query) {
    if (query.length < 2) return;
    
    $.get('/api/drugs/search', { q: query }, function(data) {
        // Update search results
        console.log('Search results:', data);
    });
}

// Form validation
function validateDrugForm() {
    const costPrice = parseFloat($('#cost_price').val());
    const sellingPrice = parseFloat($('#selling_price').val());
    
    if (sellingPrice < costPrice) {
        alert('Selling price cannot be less than cost price!');
        return false;
    }
    
    const expiryDate = new Date($('#expiry_date').val());
    const today = new Date();
    
    if (expiryDate <= today) {
        alert('Expiry date must be in the future!');
        return false;
    }
    
    return true;
}

// Print functionality
function printReport() {
    window.print();
}

// Export to CSV
function exportToCSV(tableId, filename) {
    let table = document.getElementById(tableId);
    let rows = table.querySelectorAll('tr');
    let csv = [];
    
    for (let i = 0; i < rows.length; i++) {
        let row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ');
            data = data.replace(/"/g, '""');
            row.push('"' + data + '"');
        }
        
        csv.push(row.join(','));
    }
    
    let csvString = csv.join('\n');
    let link = document.createElement('a');
    link.style.display = 'none';
    link.setAttribute('target', '_blank');
    link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvString));
    link.setAttribute('download', filename + '.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Sales calculation
function calculateSaleTotal() {
    const quantity = parseInt($('#quantity').val()) || 0;
    const unitPrice = parseFloat($('#unit_price').val().replace('$', '')) || 0;
    const total = quantity * unitPrice;
    
    $('#total_price').val('$' + total.toFixed(2));
}

// Inventory warnings
function checkInventoryLevels() {
    $('.quantity-cell').each(function() {
        const quantity = parseInt($(this).text());
        if (quantity < 10) {
            $(this).addClass('text-danger fw-bold');
        } else if (quantity < 20) {
            $(this).addClass('text-warning');
        }
    });
}

// Date formatting helpers
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US');
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US');
}

// Currency formatting
function formatCurrency(amount) {
    return '$' + parseFloat(amount).toFixed(2);
}

// Initialize when document is ready
$(document).ready(function() {
    checkInventoryLevels();
    
    // Add today's date to expiry date field by default
    const today = new Date();
    const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate());
    $('#expiry_date').val(nextMonth.toISOString().split('T')[0]);
});