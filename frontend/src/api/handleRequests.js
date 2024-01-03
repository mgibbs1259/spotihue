import axios from 'axios';

export async function getData(apiEndpoint) {
    try {
        const response = await axios.get(apiEndpoint);
        const responseData = response;
        console.log(responseData);
        return responseData;
    } catch (error) {
        const errorMessage = `Error fetching data from ${apiEndpoint}: ${error.message}`;
        console.error(errorMessage);
        throw new Error(errorMessage);
    }
};

export async function postData(apiEndpoint) {
    try {
      const response = await axios.post(apiEndpoint);
      const responseData = response;
      console.log(responseData);
      return responseData;
    } catch (error) {
      const errorMessage = `Error posting to ${apiEndpoint}: ${error.message}`;
      console.error(errorMessage);
      throw new Error(errorMessage);
    }
};