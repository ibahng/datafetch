from datafetch.base_var import Config

import yfinance as yf # type: ignore
import numpy as np # type: ignore
import requests # type: ignore
import pandas as pd # type: ignore
from datetime import timedelta, datetime

#------------------------------------------------------------------------------------------
class InvalidParameterError(Exception):
    def __init__(self, msg):
        self.msg = msg

class InvalidSecurityError(Exception):
    def __init__(self, msg: str):
        self.msg = msg

class MissingConfigObject(Exception):
    def __init__(self, msg: str):
        self.msg = msg

#------------------------------------------------------------------------------------------
class econ_indic:
#------------------------------------------------------------------------------------------
    def gdp(self, country: str = 'US', type: str = 'nominal', period: str = '5y', figure: str = 'quarter', base: str = '2020-Q1'):
        valid_params = {'valid_country': ["US", "CN", "JP", "DE", "GB", "FR", "IN", "IT", "CA", "KR", "RU", "BR", "AU", "NL", "ES", "CH", "SE", "BE", "AT", "PL", "SG", "HK", "TW", 
                                          "MX", "SA", "AE", "NG", "ZA", "ID", "NO", "QA", "IR", "KZ", "CL", "TR", "VN", "TH", "MY", "PH", "EG", "PK", "BD", "IL", "DK", "FI", "UA", 
                                          "RO", "AR", "CO", "PE", "GR", "SK", "NZ", "LU", "SI", "HU", "IS"],
                        'valid_type': ['nominal', 'real', 'deflator'],
                        'valid_period': ['1y', '2y', '5y', '10y', 'max'],
                        'valid_figure': ['quarter', 'ttm']}
        
        # United States, China, Japan, Germany, United Kingdom, France, India, Italy, Canada, South Korea, Russia, Brazil, Australia, Netherlands, Spain, Switzerland, Sweden, Belgium, Austria, Poland, Singapore, Hong Kong, Taiwan, Mexico, Saudi Arabia, United Arab Emirates, Nigeria, South Africa, Indonesia, Norway, Qatar, Iran, Kazakhstan, Chile, Türkiye, Vietnam, Thailand, Malaysia, Philippines, Egypt, Pakistan, Bangladesh, Israel, Denmark, Finland, Ukraine, Romania, Argentina, Colombia, Peru, Greece, Slovakia, New Zealand, Luxembourg, Slovenia, Hungary, Iceland
        
        params = {'country': country,
                  'type': type,
                  'period': period,
                  'figure': figure}

        for param_key, param_value, valid_param in zip(params.keys(), params.values(), valid_params.values()):
            if param_value not in valid_param:
                raise InvalidParameterError(f"Invalid {param_key} parameter '{param_value}'. "
                                            f"Please choose a valid parameter: {', '.join(valid_param)}")
            
        IMF_indicator = {
            'nominal': 'NGDP_SA_XDC',
            'real': 'NGDP_R_SA_XDC'
        }
            
        #RAW DATA/OBSERVATION--------------------------------------------------------------
        IMF_url1 = f'http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/Q.{country}.NGDP_SA_XDC'
        IMF_ngdp = requests.get(IMF_url1).json()['CompactData']['DataSet']['Series']['Obs']

        if type != 'nominal':
            IMF_url2 = f'http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/Q.{country}.NGDP_R_SA_XDC'
            IMF_rgdp = requests.get(IMF_url2).json()['CompactData']['DataSet']['Series']['Obs']
        #----------------------------------------------------------------------------------

        def is_numeric(str):
            try:
                float(str)
                return True
            except ValueError:
                return False

        #PARAMETER - TYPE ==================================================================
        quarter_to_month = {
                    'Q1': '03-01',
                    'Q2': '06-01',
                    'Q3': '09-01',
                    'Q4': '12-01',
                }
        
        if type != 'nominal':
            gdp_data = []
            for IMF_gdp in [IMF_ngdp, IMF_rgdp]:
                data = {}
                for i in IMF_gdp:
                    raw_period = i['@TIME_PERIOD']
                    value = i['@OBS_VALUE']
                    raw_year, raw_quarter = raw_period.split('-')
                    quarter = quarter_to_month[raw_quarter]
                    date = f'{raw_year}-{quarter}'
                    data[date] = (int(float(value)) if is_numeric(value) else np.nan)

                data_df = pd.DataFrame.from_dict(data, orient='index', columns=['filler'])
                gdp_data.append(data_df)

            gdp_df = pd.concat([gdp_data[0],gdp_data[1]], axis=1)
            gdp_df.columns = ['Q Nominal GDP', 'Q Raw Real GDP']
            base_date = f'{base.split('-')[0]}-{quarter_to_month[base.split('-')[1]]}'
            
            base_factor = (gdp_df['Q Nominal GDP'].loc[base_date]/gdp_df['Q Raw Real GDP'].loc[base_date])
            
            gdp_df[f'Q {base} Base Real GDP'] = (gdp_df['Q Raw Real GDP'] * base_factor).astype(int)
            del gdp_df['Q Raw Real GDP']

            output = gdp_df[f'Q {base} Base Real GDP'] # OUTPUT: Quarterly Real GDP

            if figure == 'ttm':
                gdp_df[f'TTM {base} Base Real GDP'] = gdp_df[f'Q {base} Base Real GDP'] + gdp_df[f'Q {base} Base Real GDP'].shift(1) + gdp_df[f'Q {base} Base Real GDP'].shift(2) + gdp_df[f'Q {base} Base Real GDP'].shift(3)

                output = gdp_df[f'TTM {base} Base Real GDP'] # OUTPUT: TTM Real GDP

                if type == 'deflator':
                    gdp_df['TTM Nominal GDP'] = gdp_df['Q Nominal GDP'] + gdp_df['Q Nominal GDP'].shift(1) + gdp_df['Q Nominal GDP'].shift(2) + gdp_df['Q Nominal GDP'].shift(3)
                    gdp_df[f'TTM {base} Base GDP Deflator'] = (gdp_df['TTM Nominal GDP']/gdp_df[f'TTM {base} Base Real GDP']) * 100

                    output = gdp_df[f'TTM {base} Base GDP Deflator'] # OUTPUT: TTM GDP Deflator

            if type == 'deflator' and figure == 'quarter':
                gdp_df[f'Q {base} Base GDP Deflator'] = (gdp_df['Q Nominal GDP']/gdp_df[f'Q {base} Base Real GDP']) * 100

                output = gdp_df[f'Q {base} Base GDP Deflator'] # OUTPUT: Quarterly GDP Deflator

        elif type == 'nominal':
                data = {}
                for i in IMF_ngdp:
                    raw_period = i['@TIME_PERIOD']
                    value = i['@OBS_VALUE']
                    raw_year, raw_quarter = raw_period.split('-')
                    quarter = quarter_to_month[raw_quarter]
                    date = f'{raw_year}-{quarter}'
                    data[date] = (int(float(value)) if is_numeric(value) else np.nan)
                gdp_df = pd.DataFrame.from_dict(data, orient='index', columns=['Q Nominal GDP'])

                output = gdp_df # OUTPUT: Quarterly Nominal GDP

                if figure == 'ttm':
                    gdp_df['TTM Nominal GDP'] = gdp_df['Q Nominal GDP'] + gdp_df['Q Nominal GDP'].shift(1) + gdp_df['Q Nominal GDP'].shift(2) + gdp_df['Q Nominal GDP'].shift(3)
                    
                    output = gdp_df['TTM Nominal GDP'] # OUTPUT: TTM Nominal GDP

        if figure == 'ttm':
            output = output.drop(gdp_df.index[:3])
            if type != 'deflator':
                output = output.map(lambda x: int(x) if isinstance(x, (int, float)) and pd.notna(x) else x)

        output = output.to_frame()

        #PARAMETER - PERIOD ================================================================
        period_to_points = {
            '10y': -41,
            '5y': -21,
            '2y': -9,
            '1y': -5,
        }
        
        if period == 'max':
            pass
        else:
            output = output.iloc[period_to_points[period]:]

        return output

#------------------------------------------------------------------------------------------
    def price_index(self, display: str = 'json', country: str = 'US', type: str = 'consumer', period: str = '5y'):
        valid_params = {'valid_display': ['json', 'pretty'],
                        'valid_country': ['filler', 'filler'],
                        'valid_type': ['consumer', 'export', 'import', 'producer', 'wholesale'],
                        'valid_period': ['filler']}
        
        params = {'display': display,
                  'country': country,
                  'type': type,
                  'period': period}

        for param_key, param_value, valid_param in zip(params.keys(), params.values(), valid_params.values()):
            if param_value not in valid_param:
                raise InvalidParameterError(f"Invalid {param_key} parameter '{param_value}'. "
                                            f"Please choose a valid parameter: {', '.join(valid_param)}")
            
        #IMF IFS dataset
#------------------------------------------------------------------------------------------
    def pce(self):
        #FRED US data
        pass
#------------------------------------------------------------------------------------------
    def hicp(self):
        #FRED eurozone data
        pass
#------------------------------------------------------------------------------------------
    def unemployment():
        pass
#------------------------------------------------------------------------------------------
    def labor_participation():
        pass

#------------------------------------------------------------------------------------------


#------------------------------------------------------------------------------------------