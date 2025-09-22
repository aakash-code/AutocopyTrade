document.addEventListener('DOMContentLoaded', () => {
    const credentialsForm = document.getElementById('credentials-form');
    const tradesTableBody = document.querySelector('#trades-table tbody');

    credentialsForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(credentialsForm);
        const credentials = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(credentials),
            });

            if (response.ok) {
                alert('Credentials saved successfully!');
            } else {
                alert('Failed to save credentials.');
            }
        } catch (error) {
            console.error('Error saving credentials:', error);
            alert('An error occurred while saving credentials.');
        }
    });

    const socket = new WebSocket('ws://localhost:8000/ws/trades');

    socket.onmessage = (event) => {
        const trade = JSON.parse(event.data);
        const newRow = document.createElement('tr');

        newRow.innerHTML = `
            <td>${trade.broker}</td>
            <td>${trade.symbol}</td>
            <td>${trade.transaction_type}</td>
            <td>${trade.quantity}</td>
            <td>${trade.price}</td>
            <td>${trade.status}</td>
        `;

        tradesTableBody.appendChild(newRow);
    };

    socket.onopen = () => {
        console.log('WebSocket connection established.');
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
        console.log('WebSocket connection closed.');
    };
});
