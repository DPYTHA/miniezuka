// fees_dashboard.js - Gestion des onglets et chargement des données

console.log('✅ fees_dashboard.js chargé');

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM chargé - initialisation...');
    
    // Initialisation des onglets
    initTabs();
    
    // Chargement des données initiales
    loadCurrencyFees();
    loadExchangeRates();
    loadCountries();
});

// Gestion des onglets
function initTabs() {
    console.log('🔧 Initialisation des onglets...');
    
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            console.log(`📁 Onglet cliqué: ${tabName}`);
            
            // Désactiver tous les onglets
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(tc => tc.style.display = 'none');
            
            // Activer l'onglet courant
            this.classList.add('active');
            const activeTab = document.getElementById(`${tabName}-tab`);
            if (activeTab) {
                activeTab.style.display = 'block';
            }
            
            // Charger les données de l'onglet si nécessaire
            switch(tabName) {
                case 'fees':
                    loadCurrencyFees();
                    break;
                case 'rates':
                    loadExchangeRates();
                    break;
                case 'countries':
                    loadCountries();
                    break;
            }
        });
    });
}

// Charger les frais par devise
async function loadCurrencyFees() {
    console.log('💰 Chargement des frais par devise...');
    
    try {
        const response = await fetch('/admin/api/currency_configs');
        console.log('📊 Réponse frais:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📦 Données frais reçues:', data);
        
        const tbody = document.getElementById('currency-fees-body');
        if (!tbody) {
            console.error('❌ Table body non trouvé pour currency-fees-body');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (!data.configs || data.configs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px;">Aucune configuration de devise trouvée</td></tr>';
            return;
        }
        
        data.configs.forEach(config => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${escapeHtml(config.currency_code)}</strong></td>
                <td>${escapeHtml(config.currency_name)}</td>
                <td>${config.transfer_fee_percent}%</td>
                <td>${config.withdrawal_fee_percent}%</td>
                <td><span class="status-${config.is_active ? 'active' : 'inactive'}">${config.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td>${config.updated_at ? escapeHtml(config.updated_at) : 'N/A'}</td>
                <td class="actions">
                    <button class="action-btn btn-primary" onclick="editCurrencyConfig(${config.id})">Modifier</button>
                    <button class="action-btn ${config.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleCurrencyConfig(${config.id}, ${!config.is_active})">
                        ${config.is_active ? 'Désactiver' : 'Activer'}
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        console.log(`✅ ${data.configs.length} configurations de devises chargées`);
        
    } catch (error) {
        console.error('❌ Erreur chargement frais:', error);
        const tbody = document.getElementById('currency-fees-body');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: red; padding: 20px;">Erreur lors du chargement des données</td></tr>';
        }
    }
}

// Charger les taux de change
async function loadExchangeRates() {
    console.log('💱 Chargement des taux de change...');
    
    try {
        const response = await fetch('/admin/api/exchange_rates');
        console.log('📊 Réponse taux:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📦 Données taux reçues:', data);
        
        const tbody = document.getElementById('exchange-rates-body');
        if (!tbody) {
            console.error('❌ Table body non trouvé pour exchange-rates-body');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (!data.rates || data.rates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">Aucun taux de change trouvé</td></tr>';
            return;
        }
        
        data.rates.forEach(rate => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${escapeHtml(rate.from_currency)}</strong></td>
                <td><strong>${escapeHtml(rate.to_currency)}</strong></td>
                <td>${rate.rate}</td>
                <td><span class="status-${rate.is_active ? 'active' : 'inactive'}">${rate.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td>${rate.updated_at ? escapeHtml(rate.updated_at) : 'N/A'}</td>
                <td class="actions">
                    <button class="action-btn btn-primary" onclick="editExchangeRate(${rate.id})">Modifier</button>
                    <button class="action-btn ${rate.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleExchangeRate(${rate.id}, ${!rate.is_active})">
                        ${rate.is_active ? 'Désactiver' : 'Activer'}
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        console.log(`✅ ${data.rates.length} taux de change chargés`);
        
    } catch (error) {
        console.error('❌ Erreur chargement taux:', error);
        const tbody = document.getElementById('exchange-rates-body');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red; padding: 20px;">Erreur lors du chargement des données</td></tr>';
        }
    }
}

// Charger les pays et devises
async function loadCountries() {
    console.log('🌍 Chargement des pays et devises...');
    
    try {
        const response = await fetch('/admin/api/country_currencies');
        console.log('📊 Réponse pays:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📦 Données pays reçues:', data);
        
        const tbody = document.getElementById('countries-body');
        if (!tbody) {
            console.error('❌ Table body non trouvé pour countries-body');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (!data.countries || data.countries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px;">Aucun pays trouvé</td></tr>';
            return;
        }
        
        data.countries.forEach(country => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${escapeHtml(country.country_name)}</td>
                <td><strong>${escapeHtml(country.country_code)}</strong></td>
                <td><strong>${escapeHtml(country.currency_code)}</strong></td>
                <td><span class="status-${country.is_active ? 'active' : 'inactive'}">${country.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td class="actions">
                    <button class="action-btn btn-primary" onclick="editCountryCurrency(${country.id})">Modifier</button>
                    <button class="action-btn ${country.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleCountryCurrency(${country.id}, ${!country.is_active})">
                        ${country.is_active ? 'Désactiver' : 'Activer'}
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        console.log(`✅ ${data.countries.length} pays chargés`);
        
    } catch (error) {
        console.error('❌ Erreur chargement pays:', error);
        const tbody = document.getElementById('countries-body');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: red; padding: 20px;">Erreur lors du chargement des données</td></tr>';
        }
    }
}

// Fonction utilitaire pour échapper le HTML
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Fonctions pour les modals
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Fermer les modals en cliquant à l'extérieur
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Modifier une devise
async function editCurrencyConfig(id) {
    try {
        const response = await fetch('/admin/api/currency_configs');
        const data = await response.json();
        const config = data.configs.find(c => c.id === id);
        
        if (config) {
            document.getElementById('editCurrencyId').value = config.id;
            document.getElementById('editCurrencyCode').value = config.currency_code;
            document.getElementById('editCurrencyName').value = config.currency_name;
            document.getElementById('editTransferFee').value = config.transfer_fee_percent;
            document.getElementById('editWithdrawalFee').value = config.withdrawal_fee_percent;
            document.getElementById('editCurrencyActive').checked = config.is_active;
            
            openModal('editCurrencyModal');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des données');
    }
}

// Sauvegarder une devise
async function saveCurrencyConfig() {
    const formData = {
        id: parseInt(document.getElementById('editCurrencyId').value),
        currency_name: document.getElementById('editCurrencyName').value,
        transfer_fee_percent: parseFloat(document.getElementById('editTransferFee').value),
        withdrawal_fee_percent: parseFloat(document.getElementById('editWithdrawalFee').value),
        is_active: document.getElementById('editCurrencyActive').checked
    };
    
    try {
        const response = await fetch('/admin/api/update_currency_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        if (data.success) {
            closeModal('editCurrencyModal');
            loadCurrencyFees();
            showNotification('Devise mise à jour avec succès', 'success');
        } else {
            alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la mise à jour');
    }
}

// Modifier un taux de change
async function editExchangeRate(id) {
    try {
        const response = await fetch('/admin/api/exchange_rates');
        const data = await response.json();
        const rate = data.rates.find(r => r.id === id);
        
        if (rate) {
            document.getElementById('editRateId').value = rate.id;
            document.getElementById('editFromCurrency').value = rate.from_currency;
            document.getElementById('editToCurrency').value = rate.to_currency;
            document.getElementById('editExchangeRate').value = rate.rate;
            document.getElementById('editRateActive').checked = rate.is_active;
            
            openModal('editRateModal');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des données');
    }
}

// Sauvegarder un taux de change
async function saveExchangeRate() {
    const formData = {
        id: parseInt(document.getElementById('editRateId').value),
        rate: parseFloat(document.getElementById('editExchangeRate').value),
        is_active: document.getElementById('editRateActive').checked
    };
    
    try {
        const response = await fetch('/admin/api/update_exchange_rate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        if (data.success) {
            closeModal('editRateModal');
            loadExchangeRates();
            showNotification('Taux de change mis à jour avec succès', 'success');
        } else {
            alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la mise à jour');
    }
}

// Modifier un pays
async function editCountryCurrency(id) {
    try {
        const response = await fetch('/admin/api/country_currencies');
        const data = await response.json();
        const country = data.countries.find(c => c.id === id);
        
        if (country) {
            document.getElementById('editCountryId').value = country.id;
            document.getElementById('editCountryName').value = country.country_name;
            document.getElementById('editCountryCode').value = country.country_code;
            document.getElementById('editCountryCurrency').value = country.currency_code;
            document.getElementById('editCountryActive').checked = country.is_active;
            
            openModal('editCountryModal');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des données');
    }
}

// Sauvegarder un pays
async function saveCountryCurrency() {
    const formData = {
        id: parseInt(document.getElementById('editCountryId').value),
        currency_code: document.getElementById('editCountryCurrency').value,
        is_active: document.getElementById('editCountryActive').checked
    };
    
    try {
        const response = await fetch('/admin/api/update_country_currency', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        if (data.success) {
            closeModal('editCountryModal');
            loadCountries();
            showNotification('Pays mis à jour avec succès', 'success');
        } else {
            alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la mise à jour');
    }
}

// Afficher le modal pour ajouter un taux
function showAddRateForm() {
    // Réinitialiser le formulaire
    document.getElementById('addRateForm').reset();
    openModal('addRateModal');
}

// Ajouter un nouveau taux de change
async function addNewExchangeRate() {
    const fromCurrency = document.getElementById('addFromCurrency').value;
    const toCurrency = document.getElementById('addToCurrency').value;
    const rate = document.getElementById('addExchangeRate').value;
    
    if (!fromCurrency || !toCurrency || !rate) {
        alert('Veuillez remplir tous les champs');
        return;
    }
    
    if (fromCurrency === toCurrency) {
        alert('Les devises source et cible doivent être différentes');
        return;
    }
    
    const formData = {
        from_currency: fromCurrency,
        to_currency: toCurrency,
        rate: parseFloat(rate)
    };
    
    try {
        const response = await fetch('/admin/api/add_exchange_rate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        if (data.success) {
            closeModal('addRateModal');
            loadExchangeRates();
            showNotification('Taux de change ajouté avec succès', 'success');
        } else {
            alert('Erreur lors de l\'ajout: ' + (data.error || 'Erreur inconnue'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'ajout');
    }
}

// Fonctions de toggle (activation/désactivation)
async function toggleCurrencyConfig(id, newStatus) {
    if (confirm(`Êtes-vous sûr de vouloir ${newStatus ? 'activer' : 'désactiver'} cette devise ?`)) {
        try {
            const response = await fetch('/admin/api/update_currency_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: id,
                    is_active: newStatus
                })
            });
            
            const data = await response.json();
            if (data.success) {
                loadCurrencyFees();
                showNotification(`Devise ${newStatus ? 'activée' : 'désactivée'} avec succès`, 'success');
            } else {
                alert('Erreur lors de la mise à jour');
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour');
        }
    }
}

async function toggleExchangeRate(id, newStatus) {
    if (confirm(`Êtes-vous sûr de vouloir ${newStatus ? 'activer' : 'désactiver'} ce taux ?`)) {
        try {
            const response = await fetch('/admin/api/update_exchange_rate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: id,
                    is_active: newStatus
                })
            });
            
            const data = await response.json();
            if (data.success) {
                loadExchangeRates();
                showNotification(`Taux ${newStatus ? 'activé' : 'désactivé'} avec succès`, 'success');
            } else {
                alert('Erreur lors de la mise à jour');
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour');
        }
    }
}

async function toggleCountryCurrency(id, newStatus) {
    if (confirm(`Êtes-vous sûr de vouloir ${newStatus ? 'activer' : 'désactiver'} ce pays ?`)) {
        try {
            const response = await fetch('/admin/api/update_country_currency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: id,
                    is_active: newStatus
                })
            });
            
            const data = await response.json();
            if (data.success) {
                loadCountries();
                showNotification(`Pays ${newStatus ? 'activé' : 'désactivé'} avec succès`, 'success');
            } else {
                alert('Erreur lors de la mise à jour');
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour');
        }
    }
}

// Fonction pour afficher des notifications
function showNotification(message, type = 'info') {
    // Créer une notification simple
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        z-index: 10000;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease;
    `;
    
    if (type === 'success') {
        notification.style.background = '#27ae60';
    } else if (type === 'error') {
        notification.style.background = '#e74c3c';
    } else {
        notification.style.background = '#3498db';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Fonctions de base (maintenues pour compatibilité)
function showAddCurrencyForm() {
    alert('Fonction à implémenter: Ajouter une devise');
}

// Exposer toutes les fonctions globalement
window.openModal = openModal;
window.closeModal = closeModal;
window.editCurrencyConfig = editCurrencyConfig;
window.saveCurrencyConfig = saveCurrencyConfig;
window.editExchangeRate = editExchangeRate;
window.saveExchangeRate = saveExchangeRate;
window.editCountryCurrency = editCountryCurrency;
window.saveCountryCurrency = saveCountryCurrency;
window.showAddRateForm = showAddRateForm;
window.addNewExchangeRate = addNewExchangeRate;
window.toggleCurrencyConfig = toggleCurrencyConfig;
window.toggleExchangeRate = toggleExchangeRate;
window.toggleCountryCurrency = toggleCountryCurrency;
window.showAddCurrencyForm = showAddCurrencyForm;