import json
from helper import FileHelper, S3Helper
from trp import Document
import boto3

class OutputGenerator:
    def __init__(self, documentId, response, bucketName, objectName, forms, tables, ddb, ddb_form):
        self.documentId = documentId
        self.response = response
        self.bucketName = bucketName
        self.objectName = objectName
        self.forms = forms
        self.tables = tables
        self.ddb = ddb
        self.ddb_form = ddb_form
        print("FINISHED OUTPUT GENERATOR INIT WITH DDB_FORM")

        self.outputPath = "{}-analysis/{}/".format(objectName, documentId)

        self.document = Document(self.response)

    def saveItem(self, pk, sk, output):
        # Where database is saving its output
        jsonItem = {}
        jsonItem['documentId'] = pk
        jsonItem['outputType'] = sk
        jsonItem['outputPath'] = output

        self.ddb.put_item(Item=jsonItem)

    def saveForm(self, pk, page, p):
        # Where database is saving its form details
        print("STARTED SAVEFORM FUNCTION")
        print("DOCUMENT ID: {}".format(pk))
        
        # Initiate the DynamoDB jsonItem
        jsonItem = {}
        jsonItem['documentId'] = pk

        print("ddb_form - {}".format(self.ddb_form))

        # self.ddb_form.put_item(Item=jsonItem)

        jsonItem['page'] = p

        print("STARTED FOR LOOP")
        # Export all of the document page's form's fields as key/value pairs
        for field in page.form.fields:
            if field.key and field.value:
                jsonItem[field.key.text] = str(field.value.text)
        print("FINISHED FOR LOOP")

        print("jsonItem - {}".format(jsonItem))

        # Put that thing where it belongs
        print("STARTED PUT_ITEM")
        
        self.ddb_form.put_item(Item=jsonItem)
        print("FINISHED PUT_ITEM")

    def _outputText(self, page, p):
        text = page.text
        opath = "{}page-{}-text.txt".format(self.outputPath, p)
        S3Helper.writeToS3(text, self.bucketName, opath)
        self.saveItem(self.documentId, "page-{}-Text".format(p), opath)

        textInReadingOrder = page.getTextInReadingOrder()
        opath = "{}page-{}-text-inreadingorder.txt".format(self.outputPath, p)
        S3Helper.writeToS3(textInReadingOrder, self.bucketName, opath)
        self.saveItem(self.documentId, "page-{}-TextInReadingOrder".format(p), opath)

    def _outputForm(self, page, p):
        csvData = []
        for field in page.form.fields: #Field contains a key/value pair
            csvItem  = []
            if(field.key):
                csvItem.append(field.key.text) #append key to csvFieldNames (wouldn't work with more than 1 file)
            else:
                csvItem.append("")
            if(field.value):
                csvItem.append(field.value.text)
            else:
                csvItem.append("")
            csvData.append(csvItem)
        csvFieldNames = ['Key', 'Value'] #Delete
        opath = "{}page-{}-forms.csv".format(self.outputPath, p)
        S3Helper.writeCSV(csvFieldNames, csvData, self.bucketName, opath)
        self.saveItem(self.documentId, "page-{}-Forms".format(p), opath)

    def _outputTable(self, page, p):

        csvData = []
        for table in page.tables:
            csvRow = []
            csvRow.append("Table")
            csvData.append(csvRow)
            for row in table.rows:
                csvRow  = []
                for cell in row.cells:
                    csvRow.append(cell.text)
                csvData.append(csvRow)
            csvData.append([])
            csvData.append([])

        opath = "{}page-{}-tables.csv".format(self.outputPath, p)
        S3Helper.writeCSVRaw(csvData, self.bucketName, opath)
        self.saveItem(self.documentId, "page-{}-Tables".format(p), opath)

    def run(self):

        if(not self.document.pages):
            return

        opath = "{}response.json".format(self.outputPath)
        S3Helper.writeToS3(json.dumps(self.response), self.bucketName, opath)
        self.saveItem(self.documentId, 'Response', opath)

        print("Total Pages in Document: {}".format(len(self.document.pages)))

        docText = ""

        p = 1
        for page in self.document.pages:

            opath = "{}page-{}-response.json".format(self.outputPath, p)
            S3Helper.writeToS3(json.dumps(page.blocks), self.bucketName, opath)
            self.saveItem(self.documentId, "page-{}-Response".format(p), opath)
            print("STARTED SAVEFORM IN RUN")
            self.saveForm(self.documentId, page, p)
            print("FINISHED SAVE FORM IN RUN")


            self._outputText(page, p)

            docText = docText + page.text + "\n"

            if(self.forms):
                self._outputForm(page, p)

            if(self.tables):
                self._outputTable(page, p)

            p = p + 1