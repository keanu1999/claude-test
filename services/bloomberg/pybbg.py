from __future__ import print_function

import sys
from collections import defaultdict
from datetime import date

import blpapi
import numpy as np
import pandas as pd
from pandas import DataFrame


class Pybbg():
    def __init__(self, host='localhost', port=8194):
        """
        Starting bloomberg API session
        close with session.close()
        """
        sessionOptions = blpapi.SessionOptions()
        sessionOptions.setServerHost(host)
        sessionOptions.setServerPort(port)

        self.initialized_services = set()

        self.session = blpapi.Session(sessionOptions)

        if not self.session.start():
            print("Failed to start session.")

        self.session.nextEvent()

    def service_refData(self):
        if '//blp/refdata' in self.initialized_services:
            return

        if not self.session.openService("//blp/refdata"):
            print("Failed to open //blp/refdata")

        self.session.nextEvent()
        self.refDataService = self.session.getService("//blp/refdata")
        self.session.nextEvent()
        self.initialized_services.add('//blp/refdata')

    def bdh(self, ticker_list, fld_list, start_date,
            end_date=date.today().strftime('%Y%m%d'), periodselection='DAILY',
            overrides=None, adjust=True, fx=None):
        self.service_refData()

        if isstring(ticker_list):
            ticker_list = [ticker_list]
        if isstring(fld_list):
            fld_list = [fld_list]

        if hasattr(start_date, 'strftime'):
            start_date = start_date.strftime('%Y%m%d')
        if hasattr(end_date, 'strftime'):
            end_date = end_date.strftime('%Y%m%d')

        result = []
        for t in ticker_list:
            for f in fld_list:
                request = self.refDataService.createRequest("HistoricalDataRequest")
                request.getElement("securities").appendValue(t)
                request.getElement("fields").appendValue(f)

                request.set("periodicityAdjustment", "ACTUAL")
                request.set("periodicitySelection", periodselection)

                if fx:
                    request.set("currency", fx)

                request.set("startDate", start_date)
                request.set("endDate", end_date)

                if overrides is not None:
                    overrideOuter = request.getElement('overrides')
                    for k in overrides:
                        override1 = overrideOuter.appendElement()
                        override1.setElement('fieldId', k)
                        override1.setElement('value', overrides[k])

                self.session.sendRequest(request)
                data = defaultdict(dict)

                while True:
                    ev = self.session.nextEvent(500)
                    for msg in ev:
                        ticker = msg.getElement('securityData').getElement('security').getValue()
                        fieldData = msg.getElement('securityData').getElement('fieldData')
                        for i in range(fieldData.numValues()):
                            for j in range(1, fieldData.getValue(i).numElements()):
                                data[(ticker, f)][
                                    fieldData.getValue(i).getElement(0).getValue()] = \
                                    fieldData.getValue(i).getElement(j).getValue()

                    if ev.eventType() == blpapi.Event.RESPONSE:
                        break

                data = pd.DataFrame.from_dict(data)

                if len(data) == 0:
                    data = pd.DataFrame(
                        np.nan,
                        columns=pd.MultiIndex.from_tuples([(t, f)],
                                                          names=('ticker', 'field')),
                        index=pd.date_range(start_date, end_date, freq='B')
                    )

                data.index = pd.to_datetime(data.index)
                result.append(data)

        res = pd.concat(result, axis=1).dropna(how='all')

        if len(fld_list) < 2:
            res.columns = res.columns.droplevel(1)

        return res

    def bdp(self, ticker, fld_list, overrides=None):
        self.service_refData()

        request = self.refDataService.createRequest("ReferenceDataRequest")

        if isstring(ticker):
            ticker = [ticker]

        securities = request.getElement("securities")
        for t in ticker:
            securities.appendValue(t)

        if isstring(fld_list):
            fld_list = [fld_list]

        fields = request.getElement("fields")
        for f in fld_list:
            fields.appendValue(f)

        if overrides is not None:
            overrideOuter = request.getElement('overrides')
            for k in overrides:
                override1 = overrideOuter.appendElement()
                override1.setElement('fieldId', k)
                override1.setElement('value', overrides[k])

        self.session.sendRequest(request)
        data = dict()

        while True:
            ev = self.session.nextEvent(500)
            if ev.eventType() in (blpapi.Event.RESPONSE, blpapi.Event.PARTIAL_RESPONSE):
                for msg in ev:
                    securityData = msg.getElement("securityData")

                    for i in range(securityData.numValues()):
                        fieldData = securityData.getValue(i).getElement("fieldData")
                        secId = securityData.getValue(i).getElement("security").getValue()
                        if secId not in data:
                            data[secId] = dict()

                        for field in fld_list:
                            if fieldData.hasElement(field):
                                data[secId][field] = fieldData.getElement(field).getValue()
                            else:
                                data[secId][field] = np.nan

            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame.from_dict(data)

    def bds(self, security, field, overrides=None):
        self.service_refData()

        request = self.refDataService.createRequest("ReferenceDataRequest")
        assert isstring(security)
        assert isstring(field)

        securities = request.getElement("securities")
        securities.appendValue(security)

        fields = request.getElement("fields")
        fields.appendValue(field)

        if overrides is not None:
            overrideOuter = request.getElement('overrides')
            for k in overrides:
                override1 = overrideOuter.appendElement()
                override1.setElement('fieldId', k)
                override1.setElement('value', overrides[k])

        self.session.sendRequest(request)
        data = dict()

        while True:
            ev = self.session.nextEvent(500)
            for msg in ev:
                securityData = msg.getElement("securityData")
                for i in range(securityData.numValues()):
                    fieldData = securityData.getValue(i).getElement("fieldData").getElement(field)
                    for i, row in enumerate(fieldData.values()):
                        for j in range(row.numElements()):
                            e = row.getElement(j)
                            k = str(e.name())
                            v = e.getValue()
                            if k not in data:
                                data[k] = list()
                            data[k].append(v)

            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame.from_dict(data)

    def stop(self):
        self.session.stop()


def isstring(s):
    if sys.version_info[0] == 3:
        return isinstance(s, str)
    return isinstance(s, basestring)
