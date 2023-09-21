import React, { useState } from 'react';
import { useGetData } from '../hooks/useGetData';
import ButtonContainer from '../components/ButtonContainer';
import SelectLightButton from '../components/SelectLightButton';
import PrimaryButton from '../components/PrimaryButton';

function SelectLightsContainer() {
    const [isButtonDisabled, setIsButtonDisabled] = useState(false); 

    const handleButtonClick = (lightName) => {
        sessionStorage.setItem(lightName, 'false');
        setIsButtonDisabled(true);
      };

    return (
        <ButtonContainer>
          <SelectLightButton lightName='light1'></SelectLightButton>
          <PrimaryButton text="Done" fontSize="40px" disabled={isButtonDisabled} onClick={() => handleButtonClick('light1')} />
        </ButtonContainer>
        );
}
    
export default SelectLightsContainer;