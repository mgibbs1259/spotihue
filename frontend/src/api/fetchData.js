import axios from 'axios';

export async function fetchData(apiEndpoint) {
    try {
        const response = await axios.get(apiEndpoint);
        const responseData = response.data;
        console.log(responseData);
        return response.data;
    } catch (error) {
        const errorMessage = `Error fetching data from ${apiEndpoint}: ${error.message}`;
        console.error(errorMessage);
        throw new Error(errorMessage);
    }
};
