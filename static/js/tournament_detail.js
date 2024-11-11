document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('participantSearch');
    const participantList = document.getElementById('participantList');

    searchInput.addEventListener('input', function() {
        const query = this.value;
        const tournamentId = window.location.pathname.split('/').pop();

        fetch(`/search_participants/${tournamentId}?query=${query}`)
            .then(response => response.json())
            .then(data => {
                participantList.innerHTML = '';
                data.forEach(participant => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${participant.username}</td>
                        <td>${participant.event}</td>
                    `;
                    participantList.appendChild(row);
                });
            });
    });
});
