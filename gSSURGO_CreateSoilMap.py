# gSSURGO_CreateSoilMap.py
#
# Creates a single Soil Data Viewer-type maps using gSSURGO and the sdv* attribute tables
# Uses mdstatrship* tables and sdvattribute table to populate menu
#
# 2017-07-27
#
# THINGS TO DO:
#
# Test the input MUPOLYGON featurelayer to see how many polygons are selected when compared
# to the total in the source featureclass. If there is a significant difference, consider
# applying a query filter using AREASYMBOL to limit the size of the master query table.
#
#
#
# 1.  Aggregation method "Weighted Average" can now be used for non-class soil interpretations.
#
#
# 2.   "Minimum or Maximum" and its use is now restricted to numeric attributes or attributes
#   with a corresponding domain that is logically ordered.
#
# 3.  Aggregation method "Absence/Presence" was replaced with a more generalized version
# thereof, which is referred to as "Percent Present".  Up to now, aggregation method
# "Absence/Presence" was supported for one and only one attribute, component.hydricrating.
# Percent Present is a powerful new aggregation method that opens up a lot of new possibilities,
# e.g. "bedrock within two feel of the surface".
#
# 4.  The merged aggregation engine now supports two different kinds of horizon aggregation,
# "weighted average" and "weighted sum".  For the vast majority of horizon level attributes,
# "weighted average" is used.  At the current time, the only case where "weighted sum" is used is
# for Available Water Capacity, where the water holding capacity needs to be summed rather than
# averaged.

# 5.  The aggregation process now always returns two values, rather than one, the original
# aggregated result AND the percent of the map unit that shares that rating.  For example, for
# the drainage class/dominant condition example below, the rating would be "Moderately well
# drained" and the corresponding map unit percent would be 60:
#
# 6.  A horizon or layer where the attribute being aggregated is null will now never contribute
# to the final aggregated result.  There # was a case for the second version of the aggregation
# engine where this was not true.
#
# 7.  Column sdvattribute.fetchallcompsflag is no longer needed.  The new aggregation engine was
# updated to know that it needs to # include all components whenever no component percent cutoff
# is specified and the aggregation method is "Least Limiting" or "Most # Limiting" or "Minimum or Maximum".
#
# 8.  For aggregation methods "Least Limiting" and "Most Limiting", the rating will be set to "Unknown"
# if any component has a null # rating, and no component has a fully conclusive rating (0 or 1), depending
# on the type of rule (limitation or suitability) and the # corresponding aggregation method.
#

# 2015-12-17 Depth to Water Table: [Minimum or Maximum / Lower] is not swapping out NULL values for 201.
# The other aggregation methods appear to be working properly. So the minimum is returning mostly NULL
# values for the map layer when it should return 201's.

# 2015-12-17 For Most Limiting, I'm getting some questionable results. For example 'Somewhat limited'
# may get changed to 'Not rated'

# Looking at option to map fuzzy rating for all interps. This would require redirection to the
# Aggregate2_NCCPI amd CreateNumericLayer functions. Have this working, but needs more testing.
#
# 2015-12-23  Need to look more closely at my Tiebreak implementation for Interps. 'Dwellings with
# Basements (DCD, Higher) appears to be switched. Look at Delaware 'PsA' mapunit with Pepperbox-Rosedale components
# at 45% each.
#
# 2016-03-23 Fixed bad bug, skipping last mapunit in NCCPI and one other function
#
# 2016-04-19 bNulls parameter. Need to look at inclusion/exclusion of NULL rating values for Text or Choice.
# WSS seems to include NULL values for ratings such as Hydrologic Group and Flooding
#
# Interpretation columns
# interphr is the High fuzzy value, interphrc is the High rating class
# interplr is the Low fuzzy value, interplrc is the Low rating class
# Very Limited = 1.0; Somewhat limited = 0.22
#
# NCCPI maps fuzzy values by default. It appears that 1.0 would be high productivity and
# 0.01 very low productivity. Null would be Not rated.
#
# 2017-03-03 AggregateHZ_DCP_WTA - Bug fix. Was only returning surface rating for DCP. Need to let folks know about this.
#
# 2017-07-24 Depth to Water Table, DCP bug involving nullreplacementvalue and tiebreak code.
#
# 2017-08-11 Mapping interpretations using Cointerp  very slow on CONUS gSSURGO
#
# 2017-08-14 Altered Unique values legend code to skip the map symbology section for very large layers


## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + " \n" + str(sys.exc_type)+ ": " + str(sys.exc_value) + " \n"
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in attFld method", 2)
        pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:
        for string in msg.split('\n'):
            #Add a geoprocessing message (in case this is run as a tool)
            if severity == 0:
                arcpy.AddMessage(string)

            elif severity == 1:
                arcpy.AddWarning(string)

            elif severity == 2:
                arcpy.AddError(" \n" + string)

    except:
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()

        return "???"

## ===================================================================================
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed seconds
        eTotal = end - start

        # day = 86400 seconds
        # hour = 3600 seconds
        # minute = 60 seconds

        eMsg = ""

        # calculate elapsed days
        eDay1 = eTotal / 86400
        eDay2 = math.modf(eDay1)
        eDay = int(eDay2[1])
        eDayR = eDay2[0]

        if eDay > 1:
          eMsg = eMsg + str(eDay) + " days "
        elif eDay == 1:
          eMsg = eMsg + str(eDay) + " day "

        # Calculated elapsed hours
        eHour1 = eDayR * 24
        eHour2 = math.modf(eHour1)
        eHour = int(eHour2[1])
        eHourR = eHour2[0]

        if eDay > 0 or eHour > 0:
            if eHour > 1:
                eMsg = eMsg + str(eHour) + " hours "
            else:
                eMsg = eMsg + str(eHour) + " hour "

        # Calculate elapsed minutes
        eMinute1 = eHourR * 60
        eMinute2 = math.modf(eMinute1)
        eMinute = int(eMinute2[1])
        eMinuteR = eMinute2[0]

        if eDay > 0 or eHour > 0 or eMinute > 0:
            if eMinute > 1:
                eMsg = eMsg + str(eMinute) + " minutes "
            else:
                eMsg = eMsg + str(eMinute) + " minute "

        # Calculate elapsed secons
        eSeconds = "%.1f" % (eMinuteR * 60)

        if eSeconds == "1.00":
            eMsg = eMsg + eSeconds + " second "
        else:
            eMsg = eMsg + eSeconds + " seconds "

        return eMsg

    except:
        errorMsg()
        return ""

## ===================================================================================
def get_random_color(pastel_factor = 0.5):
    return [(x+pastel_factor)/(1.0+pastel_factor) for x in [random.uniform(0,1.0) for i in [1,2,3]]]

## ===================================================================================
def color_distance(c1,c2):
    return sum([abs(x[0]-x[1]) for x in zip(c1,c2)])

## ===================================================================================
def generate_new_color(existing_colors,pastel_factor = 0.5):
    max_distance = None
    best_color = None

    for i in range(0,100):
        color = get_random_color(pastel_factor = pastel_factor)
        if not existing_colors:
            return color

        best_distance = min([color_distance(color,c) for c in existing_colors])

        if not max_distance or best_distance > max_distance:
            max_distance = best_distance
            best_color = color

        return best_color




def rand_hex_color(num=1):
  ''' Generate random hex colors, default is one,
      returning a string. If num is greater than
      1, an array of strings is returned. '''
  colors = [
    RGB_to_hex([x*255 for x in random.rand(3)])
    for i in range(num)
  ]
  if num == 1:
    return colors[0]
  else:
    return colors


def polylinear_gradient(colors, n):
  ''' returns a list of colors forming linear gradients between
      all sequential pairs of colors. "n" specifies the total
      number of desired output colors '''
  # The number of colors per individual linear gradient
  n_out = int(float(n) / (len(colors) - 1))
  # returns dictionary defined by color_dict()
  gradient_dict = linear_gradient(colors[0], colors[1], n_out)

  if len(colors) > 1:
    for col in range(1, len(colors) - 1):
      next = linear_gradient(colors[col], colors[col+1], n_out)
      for k in ("hex", "r", "g", "b"):
        # Exclude first point to avoid duplicates
        gradient_dict[k] += next[k][1:]

  return gradient_dict


def fact(n):
  ''' Memoized factorial function '''
  try:
    return fact_cache[n]
  except(KeyError):
    if n == 1 or n == 0:
      result = 1
    else:
      result = n*fact(n-1)
    fact_cache[n] = result
    return result


def bernstein(t,n,i):
  ''' Bernstein coefficient '''
  binom = fact(n)/float(fact(i)*fact(n - i))
  return binom*((1-t)**(n-i))*(t**i)


def bezier_gradient(colors, n_out=100):
  ''' Returns a "bezier gradient" dictionary
      using a given list of colors as control
      points. Dictionary also contains control
      colors/points. '''
  # RGB vectors for each color, use as control points
  RGB_list = [hex_to_RGB(color) for color in colors]
  n = len(RGB_list) - 1

  def bezier_interp(t):
    ''' Define an interpolation function
        for this specific curve'''
    # List of all summands
    summands = [
      map(lambda x: int(bernstein(t,n,i)*x), c)
      for i, c in enumerate(RGB_list)
    ]
    # Output color
    out = [0,0,0]
    # Add components of each summand together
    for vector in summands:
      for c in range(3):
        out[c] += vector[c]

    return out

  gradient = [
    bezier_interp(float(t)/(n_out-1))
    for t in range(n_out)
  ]
  # Return all points requested for gradient
  return {
    "gradient": color_dict(gradient),
    "control": color_dict(RGB_list)
  }



## ===================================================================================
def BadTable(tbl):
    # Make sure the table has data
    #
    # If has contains one or more records, return False (not a bad table)
    # If the table is empty, return True (bad table)

    try:
        if not arcpy.Exists(tbl):
            return True

        recCnt = int(arcpy.GetCount_management(tbl).getOutput(0))

        if recCnt > 0:
            return False

        else:
            return True

    except:
        errorMsg()
        return True

## ===================================================================================
def SortData(muVals, a, b, sortA, sortB):
    # Input muVals is a list of lists to be sorted. Each list must have contain at least two items.
    # Input 'a' is the first item index in the sort order (integer)
    # Item 'b' is the second item index in the sort order (integer)
    # Item sortA is a bookean for reverse sort
    # Item sortB is a boolean for reverse sort
    # Perform a 2-level sort by then by item i, then by item j.
    # Return a single list

    try:
        #PrintMsg(" \nmuVals: " + str(muVals), 1)

        if len(muVals) > 0:
            muVal = sorted(sorted(muVals, key = lambda x : x[b], reverse=sortB), key = lambda x : x[a], reverse=sortA)[0]

        else:
            muVal = muVals[0]

        #PrintMsg(str(muVal) + " <- " + str(muVals), 1)

        return muVal

    except:
        errorMsg()
        return (None, None)

## ===================================================================================
def SortData0(muVals):
    # Sort by then by item 1, then by item 0 a list of tuples containing comppct_r and rating value or index and return a single tuple

    try:
        #PrintMsg(" \nmuVals: " + str(muVals), 1)

        if len(muVals) > 0:
            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # return higher value
                muVal = sorted(sorted(muVals, key = lambda x : x[1], reverse=True), key = lambda x : x[0], reverse=True)[0]

            elif tieBreaker == dSDV["tiebreaklowlabel"]:
                muVal = sorted(sorted(muVals, key = lambda x : x[1], reverse=False), key = lambda x : x[0], reverse=True)[0]

            else:
                muVal = (None, None)

        else:
            muVal = [None, None]

        #PrintMsg("\tReturning " + str(muVal) + " from: " + str(muVals), 1)

        return muVal

    except:
        errorMsg()
        return (None, None)

## ===================================================================================
def ColorRamp(dLabels, lowerColor, upperColor):
    # For Progressive color ramps, there are no colors defined for each legend item.
    # Create a dictionary of colors based upon the upper and lower colors.
    # Key value is 'part' which is the number of colors used to define the color ramp.
    #
    # count is always equal to three and part is always zero-based
    #
    # upper and lower Color are dictionaries (keys: 0, 1, 2) with RGB tuples as values
    # Will only handle base RGB color
    # dColors = ColorRamp(dLegend["count"], len(dLabels), dLegend["LowerColor"], dLegend["UpperColor"])

    try:
        import BezierColorRamp

        labelCnt = len(dLabels)
        #PrintMsg(" \nCreating color ramp based upon " + str(labelCnt) + " legend items", 1)

        dColorID = dict()
        dRGB = dict()

        # Use dColorID to identify the Lower and Upper Colors
        dColorID[(255,0,0)] = "Red"
        dColorID[(255,255,0)] = "Yellow"
        dColorID[(0,255,0)] ="Green"  # not being used in slope color ramp
        dColorID[(0,255,255)] = "Cyan"
        dColorID[(0,0,255)] = "Blue"
        dColorID[(255,0,255)] = "Magenta"   # not being used in slope color ramp

        dRGB["red"] = (255, 0, 0)
        dRGB["yellow"] = (255, 255, 0)
        dRGB["green"] = (0, 255, 0)
        dRGB["cyan"] = (0, 255, 255)
        dRGB["blue"] = (0, 0, 255)
        dRGB["magenta"] = (255, 0, 255)


        #PrintMsg(" \nLowerColor: " + str(lowerColor), 1)
        #PrintMsg("UpperColor: " + str(upperColor) + " \n ", 1)

        dBaseColors = dict()  # basic RGB color ramp as defined by lower and upper colors
        colorList = list()
        dColors = dict()

        j = -1
        lastclr = (-1,-1,-1)

        for i in range(len(lowerColor)):

            clr = lowerColor[i]
            if clr != lastclr:
                j += 1
                dBaseColors[j] = clr
                #PrintMsg("\t" + str(j) + ". " + dColorID[clr], 1)
                colorList.append(dColorID[clr])
                lastclr = clr

            clr = upperColor[i]
            if clr != lastclr:
                j += 1
                dBaseColors[j] = clr
                #PrintMsg("\t" + str(j) + ". " + dColorID[clr], 1)
                colorList.append(dColorID[clr])
                lastclr = clr

        newColors = BezierColorRamp.Process(labelCnt, colorList)

        for i in range(len(newColors)):
            dColors[i + 1] = {"red" : newColors[i][0], "green": newColors[i][1], "blue" : newColors[i][2]}

        #PrintMsg(" \ndColors: " + str(dColors), 1)

        return dColors

    except:
        errorMsg()
        return {}

## ===================================================================================
def GetMapLegend(dAtts):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    try:
        #bVerbose = False  # This function seems to work well, but prints a lot of messages.
        global dLegend
        dLegend = dict()
        dLabels = dict()

        if bFuzzy and not dAtts["attributename"].startswith("National Commodity Crop Productivity Index"):
            # Skip map legend because the fuzzy values will not match the XML legend.
            return dict()

        arcpy.SetProgressorLabel("Getting map legend information")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        xmlString = dAtts["maplegendxml"]

        #if bVerbose:
        #    PrintMsg(" \nxmlString: " + xmlString + " \n ", 1)

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        # Iterate through XML tree, finding required elements...
        i = 0
        #dLegend = dict()
        #dLabels = dict()  # now a global
        dColors = dict()
        #dLegendElements = dict()
        legendList = list()
        legendKey = ""
        legendType = ""
        legendName = ""

        # Notes: dictionary items will vary according to legend type
        # Looks like order should be dictionary key for at least the labels section
        #
        for rec in tree.iter():

            if rec.tag == "Map_Legend":
                dLegend["maplegendkey"] = rec.attrib["maplegendkey"]

            if rec.tag == "ColorRampType":
                dLegend["type"] = rec.attrib["type"]
                dLegend["name"] = rec.attrib["name"]

                if rec.attrib["name"] == "Progressive":
                    dLegend["count"] = int(rec.attrib["count"])

            if "name" in dLegend and dLegend["name"] == "Progressive":

                if rec.tag == "LowerColor":
                    # 'part' is zero-based and related to count
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Lower Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)

                if rec.tag == "UpperColor":
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Upper Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)


            if rec.tag == "Labels":
                order = int(rec.attrib["order"])

                if dSDV["attributelogicaldatatype"].lower() == "integer":
                    # get dictionary values and convert values to integer
                    try:
                        val = int(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        #rec.attrib["label"] = label
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = int(rec.attrib["upper_value"])
                        lowerVal = int(rec.attrib["lower_value"])
                        #label = rec.attrib["label"]
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                elif dSDV["attributelogicaldatatype"].lower() == "float" and not bFuzzy:
                    # get dictionary values and convert values to float
                    try:
                        val = float(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        #rec.attrib["label"] = label
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = float(rec.attrib["upper_value"])
                        lowerVal = float(rec.attrib["lower_value"])
                        #label = rec.attrib["label"]
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                else:
                    dLabels[order] = rec.attrib   # for each label, save dictionary of values

            if rec.tag == "Color":
                # Save RGB Colors for each legend item

                # get dictionary values and convert values to integer
                red = int(rec.attrib["red"])
                green = int(rec.attrib["green"])
                blue = int(rec.attrib["blue"])
                dColors[order] = rec.attrib

            if rec.tag == "Legend_Elements":
                try:
                    dLegend["classes"] = rec.attrib["classes"]   # save number of classes (also is a dSDV value)

                except:
                    pass

        # Add the labels dictionary to the legend dictionary
        dLegend["labels"] = dLabels
        dLegend["colors"] = dColors

        # Test iteration methods on dLegend
        #PrintMsg(" \n" + dAtts["attributename"] + " Legend Key: " + dLegend["maplegendkey"] + ", Type: " + dLegend["type"] + ", Name: " + dLegend["name"] , 1)

        if bVerbose:
            PrintMsg(" \n" + dAtts["attributename"] + "; MapLegendKey: " + dLegend["maplegendkey"] + ",; Type: " + dLegend["type"] , 1)

            for order, vals in dLabels.items():
                PrintMsg("\tNew " + str(order) + ": ", 1)

                for key, val in vals.items():
                    PrintMsg("\t\t" + key + ": " + str(val), 1)

                try:
                    r = int(dColors[order]["red"])
                    g = int(dColors[order]["green"])
                    b = int(dColors[order]["blue"])
                    rgb = (r,g,b)
                    #PrintMsg("\t\tRGB: " + str(rgb), 1)

                except:
                    pass



        #if dLegend["name"] == "Progressive":
        #    dColors = ColorRamp(dLegend["count"], len(dLabels), dLegend["LowerColor"], dLegend["UpperColor"])

        if bVerbose:
            PrintMsg(" \ndLegend: " + str(dLegend), 1)

        return dLegend

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()


## ===================================================================================
def CreateStringLayer(sdvLyrFile, dLegend, outputValues):
    # OLD METHOD NOT BEING USED
    #
    #             # UNIQUE_VALUES
    # Create dummy shapefile that can be used to set up
    # UNIQUE_VALUES symbology for the final map layer. Since
    # there is no join, I am hoping that the dummy layer symbology
    # can be setup correctly and then transferred to the final
    # output layer that has the table join.
    #
    # Need to expand this to able to use defined class breaks and remove unused
    # breaks, labels.

    # SDVATTRIBUTE Table notes:
    #
    # dSDV["maplegendkey"] tells us which symbology type to use
    # dSDV["maplegendclasses"] tells us if there are a fixed number of classes (5)
    # dSDV["maplegendxml"] gives us detailed information about the legend such as class values, legend text
    #
    # *maplegendkey 1: fixed numeric class ranges with zero floor. Used only for Hydric Percent Present.
    #
    # maplegendkey 2: defined list of ordered values and legend text. Used for Corrosion of Steel, Farmland Class, TFactor.
    #
    # *maplegendkey 3: classified numeric values. Physical and chemical properties.
    #
    # maplegendkey 4: unique string values. Unknown values such as mapunit name.
    #
    # maplegendkey 5: defined list of string values. Used for Interp ratings.
    #
    # *maplegendkey 6: defined class breaks for a fixed number of classes and a color ramp. Used for pH, Slope, Depth to.., etc
    #
    # *maplegendkey 7: fixed list of index values and legend text. Used for Irrigated Capability Class, WEI, KFactor.
    #
    # maplegendkey 8: random unique values with domain values and legend text. Used for HSG, Irrigated Capability Subclass, AASHTO.
    #
    try:
        #arcpy.SetProgressorLabel("Setting up map layer for string data")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # The output feature class to be created
        dummyFC = os.path.join(env.scratchGDB, "sdvsymbology")

        # Create the output feature class with rating field
        #
        if arcpy.Exists(dummyFC):
            arcpy.Delete_management(dummyFC)

        arcpy.CreateFeatureclass_management(os.path.dirname(dummyFC), os.path.basename(dummyFC), "POLYGON")

        # Create copy of output field and add to shapefile
        # AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
        #fName = dSDV["resultcolumnname"]
        outFields = arcpy.Describe(outputTbl).fields

        for fld in outFields:
            if fld.name.upper() == dSDV["resultcolumnname"].upper():
                fType = fld.type.upper()
                fLen = fld.length
                break

        arcpy.AddField_management(dummyFC, dSDV["resultcolumnname"].upper(), fType, "", "", fLen, "", "NULLABLE")

        # Open an insert cursor for the new feature class
        #
        x1 = 0
        y1 = 0
        x2 = 1
        y2 = 1

        if not None in outputValues:
            outputValues.append(None)

        with arcpy.da.InsertCursor(dummyFC, ["SHAPE@", dSDV["resultcolumnname"]]) as cur:

            for val in outputValues:
                array = arcpy.Array()
                coords = [[x1, y1], [x1, y2], [x2, y2], [x2, y1]]

                for coord in coords:
                    pnt = arcpy.Point(coord[0], coord[1])
                    array.add(pnt)

                array.add(array.getObject(0))
                polygon = arcpy.Polygon(array)

                rec = [polygon, val]
                cur.insertRow(rec)
                x1 += 1
                x2 += 1

        #
        # Setup symbology
        # Identify temporary layer filename and path
        layerFileCopy = os.path.join(env.scratchFolder, os.path.basename(sdvLyrFile))

        # Try creating a featurelayer from dummyFC
        dummyLayer = "DummyLayer"
        arcpy.MakeFeatureLayer_management(dummyFC, dummyLayer)
        dummyDesc = arcpy.Describe(dummyLayer)
        #arcpy.SaveToLayerFile_management("DummyLayer", layerFileCopy, "ABSOLUTE", "10.1")
        #arcpy.Delete_management("DummyLayer")
        #tmpSDVLayer = arcpy.mapping.Layer(layerFileCopy)
        tmpSDVLayer = arcpy.mapping.Layer(dummyLayer)
        tmpSDVLayer.visible = False

        if bVerbose:
            PrintMsg(" \nUpdating tmpSDVLayer symbology using " + sdvLyrFile, 1)

        arcpy.mapping.UpdateLayer(df, tmpSDVLayer, arcpy.mapping.Layer(sdvLyrFile), True)

        if tmpSDVLayer.symbologyType.lower() == "other":
            # Failed to properly update symbology on the dummy layer for a second time
            raise MyError, "Failed to properly update the datasource using " + dummyFC

        # At this point, the layer is based upon the dummy featureclass
        tmpSDVLayer.symbology.valueField = dSDV["resultcolumnname"]

        return tmpSDVLayer

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def CreateNumericLayer(sdvLyrFile, dLegend, outputValues, classBV, classBL):
    #
    # POLYGON layer
    #
    # Create dummy polygon featureclass that can be used to set up
    # GRADUATED_COLORS symbology for the final map layer.
    #
    # Need to expand this to able to use defined class breaks and remove unused
    # breaks, labels.
    #
    # I saw a confusing error message related to env.scratchGDB that was corrupted.
    # The error message was ERROR 000354: The name contains invalid characters.

    # SDVATTRIBUTE Table notes:
    #
    # dSDV["maplegendkey"] tells us which symbology type to use
    # dSDV["maplegendclasses"] tells us if there are a fixed number of classes (5)
    # dSDV["maplegendxml"] gives us detailed information about the legend such as class values, legend text
    #
    # *maplegendkey 1: fixed numeric class ranges with zero floor. Used only for Hydric Percent Present.
    #
    # maplegendkey 2: defined list of ordered values and legend text. Used for Corrosion of Steel, Farmland Class, TFactor.
    #
    # *maplegendkey 3: classified numeric values. Physical and chemical properties.
    #
    # maplegendkey 4: unique string values. Unknown values such as mapunit name.
    #
    # maplegendkey 5: defined list of string values. Used for Interp ratings.
    #
    # *maplegendkey 6: defined class breaks for a fixed number of classes and a color ramp. Used for pH, Slope, Depth to.., etc
    #
    # *maplegendkey 7: fixed list of index values and legend text. Used for Irrigated Capability Class, WEI, KFactor.
    #
    # maplegendkey 8: random unique values with domain values and legend text. Used for HSG, Irrigated Capability Subclass, AASHTO.

    try:
        #arcpy.SetProgressorLabel("Setting up layer for numeric data")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg(" \nTop of CreateNumericLayer \n classBV: " + str(classBV) + " \nclassBL: " + str(classBL), 1)
            # For pH, the classBV and classBL are already set properly at this point. Need to skip any changes to
            # these two variables.

        # The temporary output feature class to be created for symbology use.

        dummyName = "sdvsymbology"
        dummyFC = os.path.join(scratchGDB, dummyName)

        # Create the output feature class
        #
        if arcpy.Exists(dummyFC):
            arcpy.Delete_management(dummyFC)
            time.sleep(1)

        arcpy.CreateFeatureclass_management(os.path.dirname(dummyFC), os.path.basename(dummyFC), "POLYGON")

        # Create copy of output field and add to shapefile
        outFields = arcpy.Describe(outputTbl).fields
        for fld in outFields:
            fName = fld.name
            fType = fld.type.upper()
            fLen = fld.length

        arcpy.AddField_management(dummyFC, dSDV["resultcolumnname"].upper(), fType, "", "", fLen)

        # Handle numeric ratings
        if dSDV["maplegendkey"] in [1, 2, 3, 6]:
            #
            #try:
                # Problem with bFuzzy for other interps besides NCCPI
            #    dLabels = dLegend["labels"]  # now a global

            #except:
            #    dLabels = dict()

            if len(outputValues) == 2:
                # Use this one if outputValues are integer with a unique values renderer
                #
                if outputValues[0] is None:
                    outputValues[0] = 0

                if outputValues[1] is None:
                    outputValues[1] = 0

                if dSDV["effectivelogicaldatatype"].lower() == "float":
                    minVal = max(float(outputValues[0]), 0)
                    maxVal = max(float(outputValues[1]), 0)


                elif dSDV["effectivelogicaldatatype"].lower() == "integer":
                    minVal = max(outputValues[0], 0)
                    maxVal = max(int(outputValues[1]), 0)

                else:
                    # Use this for an unknown range of numeric values including Nulls
                    minVal = max(min(outputValues), 0)
                    maxVal = max(max(outputValues), 0)

            else:
                # More than a single pair of values

                if dSDV["effectivelogicaldatatype"].lower() == "float":
                    minVal = min(outputValues)
                    maxVal = max(outputValues)

                elif dSDV["effectivelogicaldatatype"].lower() == "integer":
                    # Need to handle Null values
                    #PrintMsg(" \noutputValues: " + str(outputValues), 1)
                    if len(outputValues) == 0:
                        minVal = 0
                        maxVal = 0

                    else:
                        minVal = max(min(outputValues), 0)
                        maxVal = max(max(outputValues), 0)

                else:
                    # Use this for an unknown range of numeric values
                    minVal = max(min(outputValues), 0)
                    maxVal = max(max(outputValues), 0)

                if minVal is None:
                    minVal = 0

                if maxVal is None:
                    maxVal = 0

            if bVerbose:
                PrintMsg("Min: " + str(minVal) + ";  Max: " + str(maxVal), 1)

            valRange = maxVal - minVal

            if dSDV["maplegendkey"] == 1:
                # This legend will use Graduated Colors
                #
                classBV = list()
                classBL = list()

                # Need to get first and last values and then resort from high to low
                if bVerbose:
                    PrintMsg(" \nC For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)

                if len(dLabels) > 0:
                    #PrintMsg(" \nGot labels....", 1)
                    if bVerbose:
                        for key, val in dLabels.items():
                            PrintMsg("\t1 dLabels[" + str(key) + "] = " + str(val), 1)

                    if float(dLabels[1]["upper_value"]) > float(dLabels[len(dLabels)]["upper_value"]):
                        # Need to swap because legend is high-to-low
                        classBV.append(float(dLabels[len(dLabels)]["lower_value"]))
                        #PrintMsg("\tLow value: " + dLabels[len(dLabels)]["lower_value"], 1)

                        for i in range(len(dLabels), 0, -1):
                            classBV.append(float(dLabels[i]["upper_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("\tLegend Text: " + dLabels[i]["label"], 1)
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                    else:
                        # Legend is already low-to-high

                        for i in range(1, len(dLabels) + 1):
                            classBV.append(float(dLabels[i]["lower_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                        classBV.append(float(dLabels[len(dLabels)]["upper_value"]))
                        #PrintMsg("\tLast value: " + dLabels[len(dLabels)]["upper_value"], 1)


                    # Report class breaks and class break labels
                    if bVerbose:
                        PrintMsg(" \nClass Break Values for 1, 3, 6: " + str(classBV), 1)
                        PrintMsg(" \nClass Break Labels for 1, 3, 6: " + str(classBL), 1)

            elif dSDV["maplegendkey"] == 2 and dSDV["attributelogicaldatatype"].lower() == "integer":
                if bVerbose:
                    PrintMsg(" \nA For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)


            elif dSDV["maplegendkey"] == 3:
                # Physical and chemical properties, NCCPI
                # 5 numeric classes; red (low val) to blue (high val) using Natural Breaks
                #
                # Try creating 5 equal interval values within the min-max range and then
                # setting only symbology.classNum (and not classBreakValues)
                #
                # There will be no legend values or legend text for this group
                if not dSDV["maplegendclasses"] is None:

                    if valRange == 0:
                        # Only a single value in the data, don't create a 5 class legend
                        classBV = [minVal, minVal]
                        classBL = [str(minVal)]

                    else:
                        if bVerbose:
                            PrintMsg(" \nCalculating equal interval for " + str(dSDV["maplegendclasses"]) + " classes with a precision of " + str(dSDV["attributeprecision"]), 1)

                        newVal = minVal


                        if dSDV["attributeprecision"] is None:
                            interVal = round((valRange / dSDV["maplegendclasses"]), 2)
                            classBV = [newVal]

                            #for i in range(int(dLegend["classes"])):
                            for i in range(int(dSDV["maplegendclasses"])):
                                newVal += interVal
                                classBV.append(int(round(newVal, 0)))

                                if i == 0:
                                    classBL.append(str(minVal) + " - " + str(newVal))

                                else:
                                    classBL.append(str(classBV[i]) + " - " + str(newVal))

                        else:
                            #PrintMsg(" \nUsing attribute precision (" + str(dSDV["attributeprecision"] ) + ") to create " + str(dSDV["maplegendclasses"]) + " legend classes", 1)
                            interVal = round((valRange / dSDV["maplegendclasses"]), dSDV["attributeprecision"])
                            classBV = [round(newVal, dSDV["attributeprecision"])]

                            for i in range(int(dSDV["maplegendclasses"]) - 1):
                                newVal += interVal
                                classBV.append(round(newVal, dSDV["attributeprecision"]))

                                if i == 0:
                                    classBL.append(str(round(minVal, dSDV["attributeprecision"])) + " - " + str(round(newVal, dSDV["attributeprecision"])))

                                else:
                                    classBL.append(str(classBV[i]) + " - " + str(round(newVal, dSDV["attributeprecision"])))

                            # Substitute last value in classBV with maxVal
                            lastLabel = str(classBV[-1]) + " - " + str(round(maxVal, dSDV["attributeprecision"]))
                            classBV.append(round(maxVal, dSDV["attributeprecision"]))
                            classBL.append(lastLabel)

                    if bVerbose:
                        PrintMsg(" \nB For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)

                else:
                    # No sdvattribute for number of legend classes
                    pass


            elif dSDV["maplegendkey"] == 6:
                # fixed numeric class ranges such as pH, slope that have high and low values
                #
                # I think I can skip 6 because pH is already set
                pass

                #for i in range(1, len(dLabels) + 1):
                #    classBV.append(float(dLabels[i]["lower_value"]))       # class break
                #    classBL.append(dLabels[i]["label"])                    # label
                    #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                #classBV.append(float(dLabels[len(dLabels)]["upper_value"]))

        else:
            # Need to handle non-numeric legends differently
            # Probably should not even call this function?
            #
            PrintMsg(" \nMapLegendKey is not valid (" + str(dSDV["maplegendkey"]) + ")", 1)
            return None

        # Open an insert cursor for the new feature class
        #
        x1 = 0
        y1 = 0
        x2 = 1
        y2 = 1

        with arcpy.da.InsertCursor(dummyFC, ["SHAPE@", fName]) as cur:
            # Create an array object needed to create features
            #
            for i in range(len(classBV)):
                array = arcpy.Array()
                coords = [[x1, y1], [x1, y2], [x2, y2], [x2, y1]]

                for coord in coords:
                    pnt = arcpy.Point(coord[0], coord[1])
                    array.add(pnt)

                array.add(array.getObject(0))

                polygon = arcpy.Polygon(array)

                rec = [polygon, classBV[i]]
                cur.insertRow(rec)
                x1 += 1
                x2 += 1

        if not dSDV["attributeuomabbrev"] is None and len(classBL) > 0:
            #PrintMsg(" \nAdding " + dSDV["attributeuomabbrev"] + " to legend " + str(classBL[0]), 1)
            classBL[0] = classBL[0] + " (" + dSDV["attributeuomabbrev"] + ")"


        if not dSDV["attributeuomabbrev"] is None and len(classBL) == 0:
            if bVerbose:
                PrintMsg(" \nNo class break labels for " + sdvAtt + " with uom: " + dSDV["attributeuomabbrev"], 1)

        # Try creating a featurelayer from dummyFC
        dummyLayer = "DummyLayer"
        arcpy.MakeFeatureLayer_management(dummyFC, dummyLayer)
        #arcpy.mapping.AddLayer(df, tmpSDVLayer)
        #arcpy.ApplySymbologyFromLayer_management("DummyLayer", sdvLyrFile)

        # Define temporary output layer filename
        #layerFileCopy = os.path.join(env.scratchFolder, os.path.basename(sdvLyrFile))
        #arcpy.SaveToLayerFile_management("DummyLayer", layerFileCopy, "ABSOLUTE", "10.1")

        #arcpy.Delete_management("DummyLayer")  # not sure that this does anything

        # Now bring up the temporary dummy featureclass and apply symbology to it
        dummyDesc = arcpy.Describe(dummyLayer)
        #tmpSDVLayer = arcpy.mapping.Layer(layerFileCopy)
        tmpSDVLayer = arcpy.mapping.Layer(dummyLayer)
        tmpSDVLayer.visible = False
        arcpy.mapping.UpdateLayer(df, tmpSDVLayer, arcpy.mapping.Layer(sdvLyrFile), True)

        if tmpSDVLayer.symbologyType.lower() == "other":
            if tmpSDVLayer.dataSource == dummyFC:
                arcpy.ApplySymbologyFromLayer_management(tmpSDVLayer, sdvLyrFile)

                if tmpSDVLayer.symbologyType.lower() == "other":
                    # Failed to properly update symbology on the dummy layer for a second time
                    raise MyError, "Failed to properly update the datasource using " + dummyFC

        # At this point, the layer is based upon the dummy featureclass
        if dSDV["maplegendkey"] in [1, 3, 6]:
            tmpSDVLayer.symbology.valueField = fName
            tmpSDVLayer.symbology.classBreakValues = classBV
            tmpSDVLayer.symbology.classBreakLabels = classBL

        elif dSDV["maplegendkey"] in [2]:
            tmpSDVLayer.symbology.valueField = fName
            tmpSDVLayer.symbology.classValues = classBV
            tmpSDVLayer.symbology.classLabels = classBL

        return tmpSDVLayer  # This does not contain the actual data. It is a dummy layer!

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def GetNumericLegend(dLegend, outputValues):
    #
    # For Raster layers only...
    # Create final class break values and labels that can be used to create legend
    #
    # SDVATTRIBUTE Table notes:
    #
    # dSDV["maplegendkey"] tells us which symbology type to use
    # dSDV["maplegendclasses"] tells us if there are a fixed number of classes (5)
    # dSDV["maplegendxml"] gives us detailed information about the legend such as class values, legend text
    #
    # *maplegendkey 1: fixed numeric class ranges with zero floor. Used only for Hydric Percent Present.
    #
    # maplegendkey 2: defined list of ordered values and legend text. Used for Corrosion of Steel, Farmland Class, TFactor.
    #
    # *maplegendkey 3: classified numeric values. Physical and chemical properties.
    #
    # maplegendkey 4: unique string values. Unknown values such as mapunit name.
    #
    # maplegendkey 5: defined list of string values. Used for Interp ratings.
    #
    # *maplegendkey 6: defined class breaks for a fixed number of classes and a color ramp. Used for pH, Slope, Depth to.., etc
    #
    # *maplegendkey 7: fixed list of index values and legend text. Used for Irrigated Capability Class, WEI, KFactor.
    #
    # maplegendkey 8: random unique values with domain values and legend text. Used for HSG, Irrigated Capability Subclass, AASHTO.

    try:
        #arcpy.SetProgressorLabel("Setting up layer for numeric data")
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        precision = max(dSDV["attributeprecision"], 0)

        # Handle numeric ratings
        if dSDV["maplegendkey"] in [1, 2, 3, 6]:
            #
            if bVerbose:
                PrintMsg(" \noutputValues are " + str(outputValues), 1)

                try:
                    PrintMsg(" \nclassBV: " + str(classBV), 1)

                except:
                    PrintMsg(" \nMissing classBV variable", 1)
                    pass

            #PrintMsg(" \nComing into GetNumericLegend, classBV = " + str(classBV), 1)

            if len(outputValues) == 2:
                # Use this one if outputValues are integer with a unique values renderer
                #
                if outputValues[0] is None:
                    outputValues[0] = 0

                if outputValues[1] is None:
                    outputValues[1] = 0

                if dSDV["effectivelogicaldatatype"].lower() == "float":
                    minVal = max(float(outputValues[0]), 0)
                    maxVal = max(float(outputValues[1]), 0)


                elif dSDV["effectivelogicaldatatype"].lower() == "integer":
                    minVal = int(max(outputValues[0], 0))
                    maxVal = int(max(outputValues[1], 0))

                else:
                    # Use this for an unknown range of numeric values including Nulls
                    minVal = max(min(outputValues), 0)
                    maxVal = max(max(outputValues), 0)

            else:
                # More than a single pair of values
                #
                # Go ahead and set the class break values = outputValues
                #PrintMsg(" \nSetting class break values and labels using outputValues: " + str(outputValues), 1)
                classBV = list(outputValues)
                classBL = list(outputValues)

                if dSDV["effectivelogicaldatatype"].lower() == "float":
                    minVal = min(outputValues)
                    maxVal = max(outputValues)

                elif dSDV["effectivelogicaldatatype"].lower() == "integer":
                    # Need to handle Null values
                    #PrintMsg(" \noutputValues: " + str(outputValues), 1)
                    if len(outputValues) == 0:
                        minVal = 0
                        maxVal = 0

                    else:
                        minVal = int(max(min(outputValues), 0))
                        maxVal = int(max(max(outputValues), 0))

                else:
                    # Use this for an unknown range of numeric values
                    minVal = max(min(outputValues), 0)
                    maxVal = max(max(outputValues), 0)

                if minVal is None:
                    minVal = 0

                if maxVal is None:
                    maxVal = 0

            if bVerbose:
                PrintMsg("GetNumericLegend has Min: " + str(minVal) + ";  Max: " + str(maxVal), 1)

            valRange = maxVal - minVal

            if dSDV["maplegendkey"] == 2 and dSDV["attributelogicaldatatype"].lower() == "integer":
                if bVerbose:
                    PrintMsg(" \nA For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)
                pass

            elif dSDV["maplegendkey"] == 3:
                # Physical and chemical properties
                # 5 numeric classes; red (low val) to blue (high val) using Natural Breaks
                #
                # Try creating 5 equal interval values within the min-max range and then
                # setting only symbology.classNum (and not classBreakValues)
                #
                # There will be no legend values or legend text for this group
                if not dSDV["maplegendclasses"] is None:

                    if valRange == 0:
                        # Only a single value in the data, don't create a 5 class legend
                        classBV = [minVal, minVal]
                        classBL = [str(minVal)]

                    else:
                        if bVerbose:
                            PrintMsg(" \nCalculating equal interval for " + str(dSDV["maplegendclasses"]) + " classes", 1)

                        interVal = round((valRange / dSDV["maplegendclasses"]), precision)
                        newVal = minVal
                        classBV = [newVal]
                        classBL = []

                        if dSDV["attributeprecision"] is None:

                            for i in range(int(dSDV["maplegendclasses"])):
                                newVal += interVal
                                classBV.append(int(round(newVal, 0)))

                                if i == 0:
                                    classBL.append(str(int(minVal)) + " - " + str(int(newVal)))

                                else:
                                    classBL.append(str(int(classBV[i])) + " - " + str(int(newVal)))

                        else:

                            for i in range(int(dSDV["maplegendclasses"]) - 1):
                                newVal += interVal
                                classBV.append(round(newVal, dSDV["attributeprecision"]))

                                if i == 0:
                                    classBL.append(str(round(minVal, dSDV["attributeprecision"])) + " - " + str(round(newVal, dSDV["attributeprecision"])))

                                else:
                                    classBL.append(str(classBV[i]) + " - " + str(round(newVal, dSDV["attributeprecision"])))

                            # Substitute last value in classBV with maxVal
                            lastLabel = str(classBV[-1]) + " - " + str(maxVal)
                            classBV.append(maxVal)
                            classBL.append(lastLabel)

                    if bVerbose:
                        PrintMsg(" \nB For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)

            elif dSDV["maplegendkey"] == 1:
                # This legend will use Graduated Colors
                #
                classBV = list()
                classBL = list()

                # Need to get first and last values and then resort from high to low
                if bVerbose:
                    if bVerbose:
                        PrintMsg(" \nC For MapLegendKey " + str(dSDV["maplegendkey"]) + ", CreateNumericLayer set class breaks to: " + str(classBV), 1)

                if len(dLabels) > 0:
                    #PrintMsg(" \nGot labels....", 1)
                    if bVerbose:
                        for key, val in dLabels.items():
                            PrintMsg("\t2 dLabels[" + str(key) + "] = " + str(val), 1)

                    if float(dLabels[1]["upper_value"]) > float(dLabels[len(dLabels)]["upper_value"]):
                        # Need to swap because legend is high-to-low
                        classBV.append(float(dLabels[len(dLabels)]["lower_value"]))
                        #PrintMsg("\tLow value: " + dLabels[len(dLabels)]["lower_value"], 1)

                        for i in range(len(dLabels), 0, -1):
                            classBV.append(float(dLabels[i]["upper_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("\tLegend Text: " + dLabels[i]["label"], 1)
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                    else:
                        # Legend is already low-to-high

                        for i in range(1, len(dLabels) + 1):
                            classBV.append(float(dLabels[i]["lower_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                        classBV.append(float(dLabels[len(dLabels)]["upper_value"]))
                        #PrintMsg("\tLast value: " + dLabels[len(dLabels)]["upper_value"], 1)


                    # Report class breaks and class break labels
                    if bVerbose:
                        PrintMsg(" \nClass Break Values for 1, 3, 6: " + str(classBV), 1)
                        PrintMsg(" \nClass Break Labels for 1, 3, 6: " + str(classBL), 1)

            elif dSDV["maplegendkey"] == 6:
                # fixed numeric class ranges such as pH, slope that have high and low values
                classBV = list()
                classBL = list()

                for i in range(1, len(dLabels) + 1):
                    classBV.append(float(dLabels[i]["lower_value"]))       # class break
                    classBL.append(dLabels[i]["label"])                    # label
                    #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                classBV.append(float(dLabels[len(dLabels)]["upper_value"]))

        else:
            # Need to handle non-numeric legends differently
            # Probably should not even call this function?
            #
            raise MyError, "maplegendkey is not valid for a numeric legend (" + str(dSDV["maplegendkey"]) + ")"

        if not dSDV["attributeuomabbrev"] is None and len(classBL) > 0:
            #PrintMsg(" \nAdding " + dSDV["attributeuomabbrev"] + " to legend " + str(classBL[0]), 1)
            classBL[0] = str(classBL[0]) + " (" + dSDV["attributeuomabbrev"] + ")"

        if not dSDV["attributeuomabbrev"] is None and len(classBL) == 0:
            if bVerbose:
                PrintMsg(" \nNo class break labels for " + sdvAtt + " with uom: " + dSDV["attributeuomabbrev"], 1)

        return classBV, classBL

    except MyError, e:
        PrintMsg(str(e), 2)
        return [], []

    except:
        errorMsg()
        return [], []

## ===================================================================================
def CreateJSONLegend(dLegend, outputTbl, outputValues, ratingField):
    # This does not work for classes that have a lower_value and upper_value
    #
    try:
        # Input dictionary 'dLegend' contains two other dictionaries:
        #   dLabels[order]
        #    dump sorted dictionary contents into output table
        #bVerbose = True
        arcpy.SetProgressorLabel("Creating JSON map legend")
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # 2. Legend
        # original dLegend contains key:hexcode and value: legend label
        #
        # original colorlist is ordered list of hexcodes
        #
        #dLegend, colorList = ReadLegend(legendFile, dataType)

        if dLegend is None or len(dLegend) == 0:
            raise MyError, ""

        if bVerbose:
            PrintMsg(" \ndLegend name: " + dLegend["name"] + ", type: " + str(dLegend["type"]), 1)
            PrintMsg("Effectivelogicaldatatype: " + dSDV["effectivelogicaldatatype"].lower(), 1)
            PrintMsg("Maplegendkey: " + str(dSDV["maplegendkey"]), 1)
            PrintMsg(" \ndLegend: " + str(dLegend), 1)
            PrintMsg(" \nOutput Values: " + str(outputValues), 1)

        if dLegend["name"] == "Progressive":

            if dSDV["maplegendkey"] in [3] and dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string', 'vtext']:
                # This would be for text values using Progressive color ramp
                #

                #if dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string', 'vtext']:

                legendList = list()

                numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                if len(numItems) == 0:
                    raise MyError, "dLegend has no color information"

                for item in numItems:
                    #PrintMsg("\t" + str(item), 1)

                    try:
                        # PrintMsg("Getting legend info for legend item #" + str(item), 1)
                        rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                        rating = dLegend["labels"][item]["value"]
                        legendLabel = dLegend["labels"][item]["label"]
                        legendList.append([rating, legendLabel, rgb])
                        PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                    except:
                        errorMsg()

            elif dSDV["maplegendkey"] in [3, 7] and dSDV["effectivelogicaldatatype"].lower() in ["float", "integer", "choice"]:  # Added the 3 to test for NCCPI. That did not help.
                #PrintMsg(" \nCheck Maplegendkey for 7: " + str(dSDV["maplegendkey"]), 1)

                if "labels" in dLegend and len(dLegend["labels"]) > 0:
                    # Progressive color ramp for numeric values

                    # Get the upper and lower colors
                    upperColor = dLegend["UpperColor"]
                    lowerColor = dLegend["LowerColor"]

                    if outputValues and dSDV["effectivelogicaldatatype"].lower() == "choice":
                        # Create uppercase version of outputValues
                        dUpper = dict()
                        for val in outputValues:
                            dUpper[val.upper()] = val

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)

                    # For NCCPI with maplegendkey = 3 and type = 1, labels is an ordered list of label numbers
                    labels = sorted(dLegend["labels"])  # returns a sorted list of legend items

                    valueList = list()
                    #PrintMsg(" \nCreateJSONLegend outputValues: " + str(outputValues), 1)




                    if dLegend["type"] != "1":   # Not NCCPI

                        for item in labels:
                            try:
                                #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                                rating = dLegend["labels"][item]["value"]
                                legendLabel = dLegend["labels"][item]["label"]

                                if not rating in outputValues and rating.upper() in dUpper:
                                    # if the legend contains a value that has a case mismatch, update the
                                    # legend to match what is in outputValues
                                    #PrintMsg(" \nUpdating legend value for " + rating, 1)
                                    rating = dUpper[rating.upper()]
                                    legendLabel = rating
                                    dLegend["labels"][item]["label"] = rating
                                    dLegend["labels"][item]["value"] = rating

                                legendList.append([rating, legendLabel])
                                #PrintMsg("Getting legend value for legend item #" + str(item) + ": " + str(rating), 1)

                                if not rating in valueList:
                                    valueList.append(rating)

                            except:
                                errorMsg()

                    elif dLegend["type"] == "1": # This is NCCPI v3 or NirrCapClass

                        for item in labels:
                            try:
                                rating = dLegend["labels"][item]["value"]
                                legendLabel = dLegend["labels"][item]["label"]

                                if not rating in outputValues and rating.upper() in dUpper:
                                    # if the legend contains a value that has a case mismatch, update the
                                    # legend to match what is in outputValues
                                    #PrintMsg(" \nUpdating legend value for " + rating, 1)
                                    rating = dUpper[rating.upper()]
                                    legendLabel = rating
                                    dLegend["labels"][item]["label"] = rating
                                    dLegend["labels"][item]["value"] = rating

                                legendList.append([rating, legendLabel])
                                #PrintMsg("Getting legend value for legend item #" + str(item) + ": " + str(rating), 1)

                                if not rating in valueList:
                                    valueList.append(rating)

                            except:
                                errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No value data for " + sdvAtt

                    else:
                        dColors = ColorRamp(dLegend["labels"], lowerColor, upperColor)

                    # Open legendList back up and add rgb colors
                    #PrintMsg(" \ndColors" + str(dColors) + " \n ", 1)

                    for cnt, clr in dColors.items():
                        rgb = [clr["red"], clr["green"], clr["blue"], 255]
                        item = legendList[cnt - 1]
                        #item = legendList[cnt - 1]
                        item.append(rgb)
                        #PrintMsg(str(cnt) + ". '" + str(item) + "'", 0)
                        legendList[cnt - 1] = item
                        #PrintMsg(str(cnt) + ". '" + str(item) + "'", 1)


            elif dSDV["maplegendkey"] in [6]:
                if "labels" in dLegend:
                    # This legend defines a number of labels with upper and lower values, along
                    # with an UpperColor and a LowerColor ramp.
                    # examples: component slope_r, depth to restrictive layer
                    # Use the ColorRamp function to create the correct number of progressive colors


                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    #PrintMsg(" \ndLegend: " + str(dLegend), 1)
                    numItems = len(dLegend["labels"]) # returns a sorted list of legend item numbers. Fails for NCCPI v2

                    # 'LowerColor': {0: (255, 0, 0), 1: (255, 255, 0), 2: (0, 255, 255)}
                    lowerColor = dLegend["LowerColor"]
                    upperColor = dLegend["UpperColor"]

                    valueList = list()
                    dLegend["colors"] = ColorRamp(dLegend["labels"], lowerColor, upperColor)
                    #PrintMsg(" \ndLegend colors: " + str(dLegend["colors"]), 1)

                    if dLegend is None or len(dLegend["colors"]) == 0:
                        raise MyError, ""

                    for item in range(1, numItems + 1):
                        try:
                            #PrintMsg("Getting legend info for legend item #"  + str(item) + ": " + str(dLegend["colors"][item]), 1)
                            #rgb = dLegend["colors"][item]
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            maxRating = dLegend["labels"][item]['upper_value']
                            minRating = dLegend["labels"][item]['lower_value']
                            valueList.append(dLegend["labels"][item]['upper_value'])
                            valueList.append(dLegend["labels"][item]['lower_value'])

                            #rating = dLegend["labels"][item]["value"]
                            if item == 1 and dSDV["attributeuomabbrev"] is not None:
                                legendLabel = dLegend["labels"][item]["label"] + " " + str(dSDV["attributeuomabbrev"])

                            else:
                                legendLabel = dLegend["labels"][item]["label"]

                            legendList.append([minRating, maxRating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(minRating) + "',  '" + str(maxRating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No data"

                    minValue = min(valueList)

                else:
                    # no "labels" in dLegend
                    # NCCPI version 2
                    # Legend Name:Progressive Type 1 MapLegendKey 6, float
                    #
                    PrintMsg(" \nThis section is designed to handle NCCPI version 2.0. No labels for the map legend", 1)
                    legendList = []
                             


            else:
                # Logic not defined for this type of map legend
                #            
                raise MyError, "Problem creating legendList for: " + dLegend["name"] + "; maplegendkey " +  str(dSDV["maplegendkey"])  # Added the 3 to test for NCCPI. That did not help.




        elif dLegend["name"] == "Defined":

            if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:  # works for Hydric (Defined, integer with maplegendkey=1)

                if dSDV["maplegendkey"] == 1:
                    # Hydric,
                    #PrintMsg(" \ndLegend for Defined, " + dSDV["effectivelogicaldatatype"].lower() + ", maplegendkey=" + str(dSDV["maplegendkey"]) + ": \n" + str(dLegend), 1)
                    # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers
                    valueList = list()

                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            maxRating = dLegend["labels"][item]['upper_value']
                            minRating = dLegend["labels"][item]['lower_value']
                            valueList.append(dLegend["labels"][item]['upper_value'])
                            valueList.append(dLegend["labels"][item]['lower_value'])

                            #rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]
                            legendList.append([minRating, maxRating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(minRating) + "',  '" + str(maxRating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No data"
                    minValue = min(valueList)

                else:
                    # integer values
                    #
                    PrintMsg(" \ndLegend for Defined, " + dSDV["effectivelogicaldatatype"].lower() + ", maplegendkey=" + str(dSDV["maplegendkey"]) + ": \n" + str(dLegend), 1)

                    # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]
                            legendList.append([rating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()


            elif dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string', 'vtext']:
                # This would include some of the interps
                #Defined, 2, choice
                #PrintMsg(" \ncolors: " + str(dLegend["colors"]), 1)
                # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                # 4. Assemble all required legend information into a single, ordered list
                legendList = list()
                numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                for item in numItems:
                    try:
                        #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                        rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                        rating = dLegend["labels"][item]["value"]
                        legendLabel = dLegend["labels"][item]["label"]
                        legendList.append([rating, legendLabel, rgb])
                        #PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                    except:
                        errorMsg()

            else:
                raise MyError, "Problem creating legendList 3 for those parameters"

        elif dLegend["name"] == "Random":
            # This one has no colors predefined
            # Defined, 2, choice
            # PrintMsg(" \ncolors: " + str(dLegend["colors"]), 1)
            # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

            # I think I can use standard arcpy.mapping code for any Unique Values-Random Colors legend
            PrintMsg(" \nSkipping Random dLegend code", 1)


        else:
            # Logic not defined for this type of map legend
            raise MyError, "Problem creating legendList2 for those parameters"

        # Not sure what is going on here, but legendList is not right at all for ConsTreeShrub
        #
        #PrintMsg(" \nProblem with legendList in CreateJSONLegend for Cons Tree Shrub", 1)
        #PrintMsg(" \nLegend Key in CreateJSONLegend: " + str(dSDV["maplegendkey"]), 1)

        # 5. Create layer definition using JSON string

        # Let's try maplegendkey as the driver...
        if dSDV["maplegendkey"] in [1,2,4,5,6,7,8] and len(legendList) == 0:
            raise MyError, "\tNo data available for " + sdvAtt+ sdvAtt + " \n "

        if dSDV["maplegendkey"] in [1]:
            # Integer: only Hydric
            #PrintMsg(" \nGetting Defined Class Breaks as JSON", 1)
            # Missing minValue at this point
            dLayerDef = DefinedBreaksJSON(legendList, minValue, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [2]:
            # Choice, Integer: Farmland class, TFactor, Corrosion Steel
            #PrintMsg(" \nProblem 1 getting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)
            #PrintMsg(" \nProblem 2 getting Unique Values legend as JSON", 1)

        elif dSDV["maplegendkey"] in [3]:
            # Float, Integer: numeric soil properties
            #PrintMsg(" \nGetting numeric Class Breaks legend as JSON", 1)
            dLayerDef = ClassBreaksJSON(os.path.basename(outputTbl), outputValues, ratingField)

        elif dSDV["maplegendkey"] in [4]:
            # VText, String: Unique Values
            #PrintMsg(" \nGetting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [5]:
            # String: Interp rating classes
            #PrintMsg(" \nGetting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [6]:
            # FLoat, Integer: pH, Slope, Depth To...
            #PrintMsg(" \nGetting Defined Class Breaks as JSON", 1)
            # Missing minValue at this point
            if "labels" in dLegend:
                dLayerDef = DefinedBreaksJSON(legendList, minValue, os.path.basename(outputTbl), ratingField)

            else:
                dLayerDef = ClassBreaksJSON(os.path.basename(outputTbl), outputValues, ratingField)

        elif dSDV["maplegendkey"] in [7]:
            # Choice: Capability Class, WEI, Drainage class
            #PrintMsg(" \nGetting Unique 'Choice' Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [8]:
            # Random: AASHTO, HSG, NonIrr Subclass
            #PrintMsg(" \nGetting Unique 'Choice' Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        else:
            PrintMsg(" \nCreating dLayerDefinition for " + dLegend["name"] + ", " + str(dSDV["maplegendkey"]) + ", " + dSDV["effectivelogicaldatatype"].lower(), 1)

        return dLayerDef

    except MyError, e:
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()


## ===================================================================================
def ClassBreaksJSON(outputTbl, outputValues, ratingField):
    # returns JSON string for classified break values template.
    # Use this for numeric data with Progressive legend name and maplegendkey = 3
    # I believe the color ramps are always for 5 classes: red, orange, light green, light blue, dark blue.
    # Red         255,0,0
    # Orange      255,200,0
    # Light Green 182,255,143
    # Light Blue  51,194,255
    # Blue        0,0,255
    #
    # Interesting note; ArcMap legend created with this code DOES display the field Name in the TOC. This is not
    # true for Unique Values legends. The qualified field name is a property of ["drawingInfo"]["renderer"]["field"]
    #
    # Need to handle better no data or outputValues only has one value.



    # need to set:
    # d.minValue as a number
    # d.classBreakInfos which is a list containing at least two slightly different dictionaries.
    # The last one contains an additional classMinValue item
    #
    # d.classBreakInfos[0]:
    #    classMaxValue: 1000
    #    symbol: {u'color': [236, 252, 204, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 10 to 1000
    #    label: 10.0 - 1000.000000

    # d.classBreakInfos[n - 1]:  # where n = number of breaks
    #    classMaxValue: 10000
    #    classMinValue: 8000
    #    symbol: {u'color': [255, 255, 0, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 1000 to 5000
    #    label: 8000.000001 - 10000.000000
    #
    # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges

    # RGB colors:
    # 255, 0, 0 = red
    # 255, 255, 0 = yellow
    # 0, 255, 0 = green
    # 0, 255, 255 = cyan
    # 0, 0, 255 = blue

    try:
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        drawOutlines = False

        # Set outline symbology
        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        # define legend colors
        dColors = dict()
        dColors[0] = [255,0,0,255]
        dColors[1] = [255,255,0,255]
        dColors[2] = [0,255,0,255]
        dColors[3] = [0,255,255,255]
        dColors[4] = [0,0,255,255]

        dOutline = dict()
        dOutline["type"] = "esriSLS"
        dOutline["style"] = "esriSLSSolid"
        dOutline["color"] = outLineColor
        dOutline["width"] = 0.4

        #
        if len(set(outputValues)) == 1:
            classNum = 1

        else:
            classNum = 5

        maxValue = round(max(outputValues), 2)
        minValue = round(min(outputValues), 2)
        low = round(min(outputValues), 2)
        step = round(((maxValue - minValue) / float(classNum)), 2)
        legendList = list()
        #PrintMsg(" \noutputValues: " + str(outputValues), 1)

        for i in range(0, classNum, 1):
            # rating, label, rgb
            high = round(low + step, 2)

            if i == 0:
                if dSDV["attributeuomabbrev"] is None:
                    label = "<= " + str(high)

                else:
                    label = "<= " + str(high) + " " + str(dSDV["attributeuomabbrev"])

            else:
                label = "> " + str(low) + " and <= " + str(high)

            rec = [low, high, label, dColors[i]]
            legendList.append(rec)
            #PrintMsg("\t" + str(i) + ". " + str(rec), 1)  # this looks good for NCCPI
            low = round(low + step, 2)


        # Add new rating field to list of layer fields
        #d = json.loads(jsonString)

        #PrintMsg(" \nUsing new function for Defined Breaks", 1)
        r = dict() # renderer
        r["type"] = "classBreaks"
        r["classificationMethod"] =  "esriClassifyManual"
        r["field"]  = outputTbl + "." + ratingField # Needs fully qualified name with aggregation method as well.
        r["minValue"] = minValue
        #r["defaultLabel"] = "Is not rated used?"
        #ds =   {"type":"esriSFS", "style":"esriSFSSolid","color":[110,110,110,255], "outline": {"type":"esriSLS","style": "esriSLSSolid","color":[110,110,110,255],"width": 0.5}}
        #r["defaultSymbol"] = ds

        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()

        #PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        #PrintMsg(" \n\t\tLegend maximum value: " + str(maxValue), 1)
        lastMax = minValue

        # Somehow I need to read through the legendList and determine whether it is ascending or descending order
        if cntLegend > 1:
            firstRating = legendList[0][0]
            lastRating = legendList[(cntLegend - 1)][0]

            if firstRating > lastRating:
                #PrintMsg(" \nReverse legendlist", 1)
                legendList.reverse()

        # Create standard numeric legend in Ascending Order
        #
        #PrintMsg(" \n I seem to have a couple of extra items in dLegend: type=1 and name=Progressive. Where did these come from?? \n ", 1)
        if cntLegend > 0:
            dLeg = dict()

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                low, high, label, rgb = legendList[cnt]
                #PrintMsg(" \n\t\tAdding legend item: " + str(label) + ", " + str(rgb), 1)
                #dLegend = dict()
                dSymbol = dict()
                legendItems = dict()
                legendItems["classMinValue"] = low
                legendItems["classMaxValue"] = high
                legendItems["label"] = label
                legendItems["description"] = ""
                legendItems["outline"] = dOutline
                dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                legendItems["symbol"] = dSymbol
                #PrintMsg(" \nlegendItem: " + str(legendItems), 1)
                classBreakInfos.append(legendItems)


        r["classBreakInfos"] = classBreakInfos
        dLayerDef = dict()
        dRenderer = dict()
        dRenderer["renderer"] = r
        dLayerDef["drawingInfo"] = dRenderer

        #PrintMsg(" \n2. dLayerDef: \n" + str(dLayerDef), 0)  # For NCCPI this is WRONG
        test = dLayerDef['drawingInfo']['renderer']['classBreakInfos']
        #PrintMsg(" \nclassBreakInfos in ClassBreaksJSON: " + str(test), 1)

        return dLayerDef

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def UniqueValuesJSON(legendList, outputTbl, ratingField):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    # Done: I need to get rid of the non-Renderer parts of the JSON so that it matches the ClassBreaksJSON function.
    # Need to implement this in the gSSURGO Mapping tools
    #
    # Example of legendList:
    # legendList: [[u'High', u'High', [0,0,255,255], [u'Moderate', u'Moderate', [0,255,0, 255], [u'Low', u'Low', [255,0,0,255]]

    try:

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        drawOutlines = False

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        d = dict()
        r = dict()
        v = dict()

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        if len(legendList) == 0:
            raise MyError, "No data in legendList"

        for legendItem in legendList:
            #dSymbol = dict()
            rating, label, rgb = legendItem

            # calculate rgb colors
            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}
            legendItems = dict()
            legendItems["value"] = rating
            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
            legendItems["label"] = label
            legendItems["symbol"] = symbol
            uniqueValueInfos.append(legendItems)

        v["uniqueValueInfos"] = uniqueValueInfos
        v["type"] = "uniqueValue"
        v["field1"] = outputTbl + "." + ratingField
        v["field2"] = "" # not being used
        v["field3"] = "" # not being used
        v["fielddelimiter"] = ";" # not being used
        r["renderer"] = v
        d["drawingInfo"] = r

        if bVerbose:
            PrintMsg(" \nUnique Values dictionary: " + str(d), 1)

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def UniqueValuesJSONList(legendList, outputTbl, ratingField):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    # Done: I need to get rid of the non-Renderer parts of the JSON so that it matches the ClassBreaksJSON function.
    # Need to implement this in the gSSURGO Mapping tools
    #
    # Example of legendList:
    # legendList: [[u'High', u'High', [0,0,255,255], [u'Moderate', u'Moderate', [0,255,0, 255], [u'Low', u'Low', [255,0,0,255]]

    try:
        drawOutlines = False

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        d = dict()
        r = dict()
        v = dict()

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        if len(legendList) == 0:
            raise MyError, "No data in legendList"

        for legendItem in legendList:
            #dSymbol = dict()
            rating, label, rgb = legendItem

            # calculate rgb colors
            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}
            legendItems = dict()
            legendItems["value"] = rating
            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
            legendItems["label"] = label
            legendItems["symbol"] = symbol
            uniqueValueInfos.append(legendItems)

        v["uniqueValueInfos"] = uniqueValueInfos
        v["type"] = "uniqueValue"
        v["field1"] = outputTbl + "." + ratingField
        v["field2"] = "" # not being used
        v["field3"] = "" # not being used
        v["fielddelimiter"] = ";" # not being used
        r["renderer"] = v
        d["drawingInfo"] = r

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()
## ===================================================================================
def DefinedBreaksJSON(legendList, minValue, outputTbl, ratingField):
    # returns JSON string for defined break values template. Use this for Hydric, pH.
    #
    # Slope uses a color ramp, with 6 classes.It has a maplegendkey=6
    # Red         255,0,0
    # Orange      255,166,0
    # Yellowish   231,255,74
    # Cyan        112,255,210
    # Blue        59,157,255
    # Dark Blue   8,8,255

    # Min and max values are set for each class
    # need to set:
    # d.minValue as a number
    # d.classBreakInfos which is a list containing at least two slightly different dictionaries.
    # The last one contains an additional classMinValue item
    #
    # d.classBreakInfos[0]:
    #    classMaxValue: 1000
    #    symbol: {u'color': [236, 252, 204, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 10 to 1000
    #    label: 10.0 - 1000.000000

    # d.classBreakInfos[n - 1]:  # where n = number of breaks
    #    classMaxValue: 10000
    #    classMinValue: 8000
    #    symbol: {u'color': [255, 255, 0, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 1000 to 5000
    #    label: 8000.000001 - 10000.000000
    #
    # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges

    # RGB colors:
    # 255, 0, 0 = red
    # 255, 255, 0 = yellow
    # 0, 255, 0 = green
    # 0, 255, 255 = cyan
    # 0, 0, 255 = blue

    try:
        if bVerbose:
            PrintMsg(" \n \n \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        drawOutlines = False

        # Set outline symbology
        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        #PrintMsg(" \nUsing new function for Defined Breaks", 1)
        r = dict() # renderer
        r["type"] = "classBreaks"
        r["classificationMethod"] =  "esriClassifyManual"
        r["field"]  = outputTbl + "." + ratingField # Needs fully qualified name with aggregation method as well.
        r["minValue"] = minValue
        r["defaultLabel"] = "Not rated or not available"
        ds = {"type":"esriSFS", "style":"esriSFSSolid","color":[110,110,110,255], "outline": {"type":"esriSLS","style": "esriSLSSolid","color":outLineColor,"width": 0.5}}
        r["defaultSymbol"] = ds


        # Add new rating field (fully qualified name) to list of layer fields

        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()

        #PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        #PrintMsg(" \n\t\tLegend maximum value: " + str(maxValue), 1)
        lastMax = minValue

        # Somehow I need to read through the legendList and determine whether it is ascending or descending order
        if cntLegend > 1:

            #for legendInfo in legendList:
            firstRating = legendList[0][0]
            lastRating = legendList[(cntLegend - 1)][0]

        if firstRating > lastRating:
            legendList.reverse()

        # Create standard numeric legend in Ascending Order
        #
        if cntLegend > 1:
            #PrintMsg(" \nChecking legendList: \n" + str(legendList), 1)

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                minRating, maxRating, label, rgb = legendList[cnt]
                if not minRating is None:

                    #ratingValue = float(rating)
                    #PrintMsg(" \n\t\tAdding legend values: " + str(lastMax) + "-> " + str(rating) + ", " + str(label), 1)

                    # calculate rgb colors
                    #rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    #rgb.append(255)  # set transparency ?
                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = minRating
                    dLegend["classMaxValue"] = maxRating
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = outLineColor
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    dLegend["outline"] = dOutline
                    classBreakInfos.append(dLegend)  # This appears to be working properly
                    #PrintMsg(" \n\t" + str(cnt) + ". Adding dLegend: " + str(dSymbol), 1)

                    #lastMax = ratingValue

                    cnt += 1  # why is cnt being incremented here????

        r["classBreakInfos"] = classBreakInfos
        dLayerDef = dict()
        dRenderer = dict()
        dRenderer["renderer"] = r
        dLayerDef["drawingInfo"] = dRenderer

        # Note to self. Hydric is running this DefinedBreaksJSON
        #PrintMsg(" \nDefinedBreaksJSON - dClassBreakInfos: \n" + str(classBreakInfos), 1)

        return dLayerDef

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def CreateStringLayer(sdvLyrFile, dLegend, outputValues):
    # Create dummy shapefile that can be used to set up
    # UNIQUE_VALUES symbology for the final map layer. Since
    # there is no join, I am hoping that the dummy layer symbology
    # can be setup correctly and then transferred to the final
    # output layer that has the table join.
    #
    # Need to expand this to able to use defined class breaks and remove unused
    # breaks, labels.

    # SDVATTRIBUTE Table notes:
    #
    # dSDV["maplegendkey"] tells us which symbology type to use
    # dSDV["maplegendclasses"] tells us if there are a fixed number of classes (5)
    # dSDV["maplegendxml"] gives us detailed information about the legend such as class values, legend text
    #
    # *maplegendkey 1: fixed numeric class ranges with zero floor. Used only for Hydric Percent Present.
    #
    # maplegendkey 2: defined list of ordered values and legend text. Used for Corrosion of Steel, Farmland Class, TFactor.
    #
    # *maplegendkey 3: classified numeric values. Physical and chemical properties.
    #
    # maplegendkey 4: unique string values. Unknown values such as mapunit name.
    #
    # maplegendkey 5: defined list of string values. Used for Interp ratings.
    #
    # *maplegendkey 6: defined class breaks for a fixed number of classes and a color ramp. Used for pH, Slope, Depth to.., etc
    #
    # *maplegendkey 7: fixed list of index values and legend text. Used for Irrigated Capability Class, WEI, KFactor.
    #
    # maplegendkey 8: random unique values with domain values and legend text. Used for HSG, Irrigated Capability Subclass, AASHTO.
    #
    try:
        #arcpy.SetProgressorLabel("Setting up map layer for string data")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # The output feature class to be created
        dummyFC = os.path.join(env.scratchGDB, "sdvsymbology")

        # Create the output feature class with rating field
        #
        if arcpy.Exists(dummyFC):
            arcpy.Delete_management(dummyFC)

        arcpy.CreateFeatureclass_management(os.path.dirname(dummyFC), os.path.basename(dummyFC), "POLYGON")

        # Create copy of output field and add to shapefile
        # AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
        #fName = dSDV["resultcolumnname"]
        outFields = arcpy.Describe(outputTbl).fields

        for fld in outFields:
            if fld.name.upper() == dSDV["resultcolumnname"].upper():
                fType = fld.type.upper()
                fLen = fld.length
                break

        arcpy.AddField_management(dummyFC, dSDV["resultcolumnname"].upper(), fType, "", "", fLen, "", "NULLABLE")

        # Open an insert cursor for the new feature class
        #
        x1 = 0
        y1 = 0
        x2 = 1
        y2 = 1

        if not None in outputValues:
            outputValues.append(None)

        with arcpy.da.InsertCursor(dummyFC, ["SHAPE@", dSDV["resultcolumnname"]]) as cur:

            for val in outputValues:
                array = arcpy.Array()
                coords = [[x1, y1], [x1, y2], [x2, y2], [x2, y1]]

                for coord in coords:
                    pnt = arcpy.Point(coord[0], coord[1])
                    array.add(pnt)

                array.add(array.getObject(0))
                polygon = arcpy.Polygon(array)

                rec = [polygon, val]
                cur.insertRow(rec)
                x1 += 1
                x2 += 1

        #
        # Setup symbology
        # Identify temporary layer filename and path
        layerFileCopy = os.path.join(env.scratchFolder, os.path.basename(sdvLyrFile))

        # Try creating a featurelayer from dummyFC
        dummyLayer = "DummyLayer"
        arcpy.MakeFeatureLayer_management(dummyFC, dummyLayer)
        dummyDesc = arcpy.Describe(dummyLayer)
        #arcpy.SaveToLayerFile_management("DummyLayer", layerFileCopy, "ABSOLUTE", "10.1")
        #arcpy.Delete_management("DummyLayer")
        #tmpSDVLayer = arcpy.mapping.Layer(layerFileCopy)
        tmpSDVLayer = arcpy.mapping.Layer(dummyLayer)
        tmpSDVLayer.visible = False

        if bVerbose:
            PrintMsg(" \nUpdating tmpSDVLayer symbology using " + sdvLyrFile, 1)

        arcpy.mapping.UpdateLayer(df, tmpSDVLayer, arcpy.mapping.Layer(sdvLyrFile), True)

        if tmpSDVLayer.symbologyType.lower() == "other":
            # Failed to properly update symbology on the dummy layer for a second time
            raise MyError, "Failed to properly update the datasource using " + dummyFC

        # At this point, the layer is based upon the dummy featureclass
        tmpSDVLayer.symbology.valueField = dSDV["resultcolumnname"]

        return tmpSDVLayer

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def CreateMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, dLayerDefinition):
    # Setup new map layer with appropriate symbology and add it to the table of contents.
    #
    # Quite a few global variables being called here.
    #
    # With ArcGIS 10.1, there seem to be major problems when the layer is a featurelayer
    # and the valueField is from a joined table. Any of the methods that try to
    # update the legend values will fail and possibly crash ArcMap.
    #
    # A new test using MakeQueryTable seems to work, but still flaky.
    #
    # Need to figure out why the symbols for Progressive allow the outlines to
    # be turned off, but 'Defined' do not.
    #
    #
    try:
        msg = "Preparing new soil map layer..."
        arcpy.SetProgressorLabel(msg)
        PrintMsg("\t" + msg, 0)

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        hasJoin = False

        # Create initial map layer using MakeQueryTable. Need to add code to make
        # sure that a join doesn't already exist, thus changind field names
        tableList = [inputLayer, outputTbl]
        joinSQL = os.path.basename(fc) + '.MUKEY = ' + os.path.basename(outputTbl) + '.MUKEY'

        # Create fieldInfo string
        dupFields = list()
        keyField = os.path.basename(fc) + ".OBJECTID"
        fieldInfo = list()
        sFields = ""

        # first get list of fields from mupolygon layer
        for fld in muDesc.fields:
            dupFields.append(fld.baseName)
            fieldInfo.append([os.path.basename(fc) + "." + fld.name, ''])

            if sFields == "":
                sFields = os.path.basename(fc) + "." + fld.name + " " + fld.baseName + " VISIBLE; "
            else:
                sFields = sFields + os.path.basename(fc) + "." + fld.name + " " + fld.baseName + " VISIBLE; "

        # then get non-duplicate fields from output table
        for fld in tblDesc.fields:
            if not fld.baseName in dupFields:
                dupFields.append(fld.baseName)
                fieldInfo.append([os.path.basename(outputTbl) + "." + fld.name, ''])
                sFields = sFields + os.path.basename(outputTbl) + "." + fld.name + " " + fld.baseName + " VISIBLE; "
                #PrintMsg("\tAdding output table field '" + fld.baseName + "' to field info", 1)

            else:
                # Use this next line for MakeFeatureLayer field info string
                sFields = sFields + os.path.basename(outputTbl) + "." + fld.name + " " + fld.baseName + " HIDDEN; "

        # Alternative is to use MakeFeatureLayer to create initial layer with join
        arcpy.AddJoin_management (inputLayer, "MUKEY", outputTbl, "MUKEY", "KEEP_ALL")
        hasJoin = True
        arcpy.MakeFeatureLayer_management(inputLayer, outputLayer, "", "", sFields)



        # identify layer file in script directory to use as basis for symbology
        #
        if bFuzzy:
            sdvLyr = "SDV_InterpFuzzyNumbers.lyr"

        else:
            if dLegend["name"] == "Random":
                sdvLyr = "SDV_PolygonUnique.lyr"

            elif dSDV["maplegendkey"] == 2 and dSDV["attributelogicaldatatype"].lower() == "integer":
                sdvLyr = "SDV_" + str(dSDV["maplegendkey"]) + "_" + str(dLegend["type"]) + "_" + dLegend["name"] + "Integer" + ".lyr"

            else:
                sdvLyr = "SDV_" + str(dSDV["maplegendkey"]) + "_" + str(dLegend["type"]) + "_" + dLegend["name"] + ".lyr"

        sdvLyrFile = os.path.join(os.path.dirname(sys.argv[0]), sdvLyr)
        #

        if bVerbose:
            PrintMsg(" \nCreating symLayer using SDV symbology from '" + sdvLyrFile + "'", 1)

        if arcpy.Exists(outputLayer):
            outputFields = [fld.name for fld in arcpy.Describe(outputLayer).fields]

            if arcpy.Exists(outputLayerFile):
                arcpy.Delete_management(outputLayerFile)

            if bVerbose:
                PrintMsg(" \nSaving " + outputLayer + " to " + outputLayerFile, 1)

            arcpy.SaveToLayerFile_management(outputLayer, outputLayerFile, "ABSOLUTE")

            try:
                arcpy.Delete_management(outputLayer)

            except:
                PrintMsg(" \nFailed to remove " + outputLayer, 1)

            if bVerbose:
                PrintMsg(" \nSaved map to layerfile: " + outputLayerFile, 0)

        else:
            raise MyError, "Could not find temporary layer: " + outputLayer + " from " + inputLayer

        if dLegend["name"] == "Random":
            #
            # New code for unique values, random color featurelayer. This skips most of the CreateMapLayer function
            # which uses JSON to build map symbology.
            #
            # I may want to incorporate layer.getSelectionSet() in order to determine if there is a selected set
            # Tip. Apply a selection set using .setSelectionSet(selSet)

            # PrintMsg(" \nUpdating layer symbology using " + sdvLyr, 1)
            start = time.time()
            symLayer = arcpy.mapping.Layer(sdvLyrFile)
            finalMapLayer = arcpy.mapping.Layer(outputLayerFile)  # recreate the outputlayer
            arcpy.mapping.UpdateLayer(df, finalMapLayer, symLayer, True)

            if finalMapLayer.symbologyType.upper() == 'UNIQUE_VALUES':

                #PrintMsg(" \nFields: " + ", ".join(outputFields), 1)
                finalMapLayer.symbology.valueField = os.path.basename(outputTbl) + "." + outputFields[-1]
                outputNum = len(outputValues)
                maxValues = 10000

                if outputNum < maxValues:
                    # If the number of unique values is less than maxValues, go ahead and create the map legend,
                    # otherwise skip it or we'll be here all day..
                    #
                    finalMapLayer.symbology.addAllValues()
                    arcpy.RefreshActiveView()
                    arcpy.RefreshTOC()
                    #theMsg = " \nUpdated symbology for " + Number_Format(outputNum, 0, True) + " unique values in " + elapsedTime(start)
                    #PrintMsg(theMsg, 0)
                    #end = time.time()
                    #lps = len(outputValues) / (end - start)
                    #PrintMsg(" \nProcessed " + Number_Format(lps, 0, True) + " labels per second", 1)

                else:
                    PrintMsg(" \nSkipping random color symbology. " + Number_Format(outputNum, 0, True) + " is too many unique values)", 0)

        else:
            # Handle all the non-Random legends

            # This next section is where classBV is getting populated for pH for Polygon
            #
            if dSDV["maplegendkey"] in [1, 3, 6]:
                # This legend will use Graduated Colors
                #
                classBV = list()
                classBL = list()

                if len(dLabels) > 0:
                    #PrintMsg(" \nGot labels....", 1)
                    if bVerbose:
                        for key, val in dLabels.items():
                            PrintMsg("\t3 dLabels[" + str(key) + "] = " + str(val), 1)

                    if float(dLabels[1]["upper_value"]) > float(dLabels[len(dLabels)]["upper_value"]):
                        # Need to swap because legend is high-to-low
                        classBV.append(float(dLabels[len(dLabels)]["lower_value"]))
                        #PrintMsg("\tLow value: " + dLabels[len(dLabels)]["lower_value"], 1)

                        for i in range(len(dLabels), 0, -1):
                            classBV.append(float(dLabels[i]["upper_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("\tLegend Text: " + dLabels[i]["label"], 1)
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                    else:
                        # Legend is already low-to-high

                        for i in range(1, len(dLabels) + 1):
                            classBV.append(float(dLabels[i]["lower_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                        classBV.append(float(dLabels[len(dLabels)]["upper_value"]))
                        #PrintMsg("\tLast value: " + dLabels[len(dLabels)]["upper_value"], 1)

                    # Report class breaks and class break labels
                    if bVerbose:
                        PrintMsg(" \nClass Break Values for 1, 3, 6: " + str(classBV), 1)
                        PrintMsg(" \nClass Break Labels for 1, 3, 6: " + str(classBL), 1)

            elif dSDV["maplegendkey"] in [2]:
                # I believe this is Unique Values renderer
                #
                # iterate through dLabels using the key 'order' to determine sequence within the map legend
                #
                labelText = list()
                dOrder = dict()    # test. create dictionary with key = uppercase(value) and contains a tuple (order, labeltext)
                classBV = list()
                classBL = list()

                if dSDV["effectivelogicaldatatype"].lower() == "integer":

                    for val in outputValues:
                        classBV.append(val)
                        classBL.append(str(val))

                else:
                    for i in range(1, len(dLabels) + 1):
                        label = dLabels[i]["label"]

                        if dSDV["effectivelogicaldatatype"].lower() == "float":
                            # Float
                            value = float(dLabels[i]["value"])    # Trying to get TFactor working

                        else:
                            # String or Choice
                            value = dLabels[i]["value"]    # Trying to get TFactor working

                        if value.upper() in domainValuesUp and not value in domainValues:
                            # Compare legend values to domainValues
                            PrintMsg("\tFixing label value: " + str(value), 1)
                            value = dValues[value.upper()][1]

                        #elif not value.upper() in domainValuesUp and not value in domainValues:
                            # Compare legend values to domainValues
                            #PrintMsg("\tExtra label value?: " + str(value), 1)
                            #value = dValues[value.upper()]

                        labelText.append(label)
                        dOrder[str(value).upper()] = (i, value, label)
                        classBV.append(value) # 10-02 Added this because of TFactor failure
                        classBL.append(label) # 10-02 Added this because of TFactor failure

            elif dSDV["maplegendkey"] in [5, 7, 8]:
                # iterate through dLabels using the key 'order' to determine sequence within the map legend
                # Added method to handle Not rated for interps
                # Need to add method to handle NULL in interps
                #
                # Includes Soil Taxonomy  4, 0, Random
                #
                #labelText = list()
                dOrder = dict()    # test. create dictionary with key = uppercase(value) and contains a tuple (order, labeltext)
                classBV = list()
                classBL = list()

                for i in range(1, len(dLabels) + 1):
                    # Make sure label value is in domainValues
                    label = dLabels[i]["label"]
                    value = dLabels[i]["value"]

                    if value.upper() in domainValuesUp and not value in domainValues:
                        # Compare legend values to domainValues
                        #PrintMsg("\tFixing label value: " + str(value), 1)
                        value = dValues[value.upper()][1]
                        label = str(value)
                        domainValues.append(value)

                    elif not value.upper() in domainValuesUp and not value in domainValues and value.upper() in dValues:
                        # Compare legend values to domainValues
                        #PrintMsg("\tExtra label value?: " + str(value), 1)
                        value = dValues[value.upper()][1]
                        label = str(value)
                        domainValues.append(value)

                    if not value in classBV:
                        dOrder[value.upper()] = (i, value, label)
                        classBV.append(value)
                        classBL.append(str(value))
                        #labelText.append(str(value))
                        #PrintMsg("\tAdded class break and label values to legend: " + str(value), 1)

                # Compare outputValues to classBV. In conservation tree/shrub, there can be values that
                # were not included in the map legend.
                for value in outputValues:
                    if not value in classBV:
                        #PrintMsg("\tAdding missing Value '" + str(value) + " to map legend", 1)
                        classBV.append(value)
                        classBL.append(value)
                        i += 1
                        dOrder[str(value).upper()] = (i, value, value)  # Added str function on value to fix bNulls error

                if "Not Rated" in outputValues:
                    #PrintMsg(" \nFound the 'Not Rated' value in outputValues", 1)
                    dOrder["NOT RATED"] = (i + 1, "Not Rated", "Not Rated")

                elif "Not rated" in outputValues:
                    #PrintMsg(" \nFound the 'Not rated' value in outputValues", 1)
                    dOrder["NOT RATED"] = (i + 1, "Not rated", "Not rated")

            if bVerbose:
                PrintMsg(" \nfinalMapLayer created using " + outputLayerFile, 1)

            finalMapLayer = arcpy.mapping.Layer(outputLayerFile)  # recreate the outputlayer


            # Test JSON formatting method
            #
            #PrintMsg(" \nUpdating layer symbology using JSON method", 1)
            #PrintMsg(" \nJSON layer update: " + str(dLayerDefinition) + " \n ", 1)
            finalMapLayer.updateLayerFromJSON(dLayerDefinition)
            #
            #



        # Remove join on original map unit polygon layer
        arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))

        # Add layer file path to layer description property
        # parameterString = parameterString + "\r\n" + "LayerFile: " + outputLayerFile

        finalMapLayer.description = dSDV["attributedescription"] + "\r\n\r\n" + parameterString
        finalMapLayer.visible = False
        arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
        arcpy.RefreshTOC()
        arcpy.SaveToLayerFile_management(finalMapLayer.name, outputLayerFile)
        PrintMsg("\tSaved map to layer file: " + outputLayerFile + " \n ", 0)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        try:
            if hasJoin:
            #    PrintMsg("\tRemoving join", 1)
                arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))

        except:
            pass

        return False

    except:
        errorMsg()
        if hasJoin:
            arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))
        return False

## ===================================================================================
def CreateRasterMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString):
    # Setup new raster map layer with appropriate symbology and add it to the table of contents.
    #
    # Progressive, numeric legend will be "RASTER_CLASSIFIED"
    #
    #
    try:
        arcpy.SetProgressorLabel("Adding map layer to table of contents")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # arcpy.mapping stuff
        #
        # mxd = arcpy.mapping.MapDocument("CURRENT")
        # df = mxd.activeDataFrame
        # layer = arcpy.mapping.ListLayers(mxd, outputLayer, df)[0]
        # arcpy.mapping.UpdateLayer(df, inLayer, symLayer, True)

        if bVerbose:
            PrintMsg(" \nAdding join to input raster layer", 1)

        # Identify possible symbology mapping layer from template layer file in script directory
        uniqueLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterUnique.lyr")
        uniqueLayer = arcpy.mapping.Layer(uniqueLayerFile)  # At 10.5 the symbology property is not supported at all. Had to add a check.
        
        # Probably need to create these layers further down the road. May not use them for TEXT values
        classLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterClassified.lyr") # SDV_RasterClassified.lyr
        classLayer = arcpy.mapping.Layer(classLayerFile)

        tmpLayerFile = os.path.join(env.scratchFolder, "tmpSDVLayer.lyr")

        if arcpy.Exists(tmpLayerFile):
            arcpy.Delete_management(tmpLayerFile)

        tmpRaster = "Temp_Raster"
        if arcpy.Exists(tmpRaster):
            # clean up any previous runs
            arcpy.Delete_management(tmpRaster)

        # Get FGDB raster from inputLayer
        inputRaster = arcpy.Describe(inputLayer).catalogPath
        arcpy.MakeRasterLayer_management(inputRaster, tmpRaster)

        if not arcpy.Exists(tmpRaster):
            raise MyError, "Missing raster map layer 1"

        arcpy.AddJoin_management (tmpRaster, "MUKEY", outputTbl, "MUKEY", "KEEP_ALL")

        if not arcpy.Exists(tmpRaster):
            raise MyError, "Missing raster map layer 2"

        if bVerbose:
            PrintMsg(" \nCreating raster layer with join (" + tmpLayerFile +  ")", 1)
            PrintMsg("\tAttributeLogicalDatatype = " + dSDV["attributelogicaldatatype"].lower(), 1)
            PrintMsg("\tOutput Table Rating Field: " + dFieldInfo[dSDV["resultcolumnname"].upper()][0], 1)

        symField = os.path.basename(outputTbl) + "." + dSDV["resultcolumnname"]
        tmpField = os.path.basename(fc) + "." + "SPATIALVER"
        #
        # Create temporary layer file using input layer with join.
        # This is only neccessary so that I can add it back in as an arcpy.mapping layer
        #arcpy.SaveToLayerFile_management(tmpRaster, tmpLayerFile, "ABSOLUTE")

        # Create final mapping layer from input raster layer.
        #
        time.sleep(1)
        finalMapLayer = arcpy.mapping.Layer(tmpRaster)  # create arcpy.mapping
        finalMapLayer.name = outputLayer
        #arcpy.mapping.AddLayer(df, finalMapLayer)

        if bVerbose:
            PrintMsg(" \nCreated '" + outputLayer + "' using " + tmpLayerFile, 1)
        #

        # Get UNIQUE_VALUES legend information for 5, 7, 8 (non-numeric?)
        #
        if dFieldInfo[dSDV["resultcolumnname"].upper()][0] == "TEXT":
            # iterate through dLabels using the key 'order' to determine sequence within the map legend
            # Added method to handle Not rated for interps
            # Need to add method to handle NULL in interps
            #
            # Includes Soil Taxonomy  4, 0, Random
            #
            labelText = list()
            dOrder = dict()    # test. create dictionary with key = uppercase(value) and contains a tuple (order, labeltext)
            classBV = list()
            classBL = list()

            for i in range(1, len(dLabels) + 1):
                label = dLabels[i]["label"]
                value = dLabels[i]["value"]
                labelText.append(label)
                dOrder[value.upper()] = (i, value, label)
                classBV.append(value) # 10-02 Added this because of TFactor failure
                classBL.append(label) # 10-02 Added this because of TFactor failure

            if "Not Rated" in outputValues:
                dOrder["NOT RATED"] = (i + 1, "Not Rated", "Not Rated")

            elif "Not rated" in outputValues:
                dOrder["NOT RATED"] = (i + 1, "Not rated", "Not rated")

            if finalMapLayer.supports("symbology") == False or finalMapLayer.symbologyType.upper() == "OTHER":
                # Failed to get UNIQUE_VALUES renderer for raster. Print help message instead.
                PrintMsg("\tThe user must manually set 'Unique Values' symbology for this raster layer using the '" + symField + "' field", 1)

            else:
                if bVerbose:
                    PrintMsg(" \nUpdating raster layer symbology to " + symbologyType + "...", 1)

                finalMapLayer.symbology.valueField = symField
                finalMapLayer.symbology.classValues = classBV

                if len(classBL)> 0:
                    finalMapLayer.symbology.classLabels = classBL # Got comppct symbology without this line

        else:
            # CLASSIFIED (numeric values)

            # Get legend values and labels
            #PrintMsg(" \noutputValues before GetNumericLegend function: " + str(outputValues), 1)

            classBV, classBL = GetNumericLegend(dLegend, outputValues)

            #PrintMsg(" \nOutput values (" + dFieldInfo[dSDV["resultcolumnname"].upper()][0] + ") " + str(outputValues), 1)

            if bVerbose:
                PrintMsg(" \nSetting arcpy.mapping symbology using " + symField + "; " + str(classBV) + "; " + str(classBL))

            # Update layer symbology using template layer file
            arcpy.mapping.UpdateLayer(df, finalMapLayer, classLayer, True)

            # Set symbology properties using information from GetNumericLegend
            finalMapLayer.symbology.valueField = symField

            # TFactor problem. Try inserting 0 into classBV

            if len(classBV) == len(classBL):
                # For numeric legends using class break values, there needs to be a starting value in addition
                # to the class breaks. This means that there are one more value than there are labels
                #PrintMsg(" \nInserting zero into class break values", 1)
                classBV.insert(0, 0)

            finalMapLayer.symbology.classBreakValues = classBV

            if len(classBL)> 0:
                finalMapLayer.symbology.classBreakLabels = classBL # Got comppct symbology without this line

        if bVerbose:
            PrintMsg(" \nCompleted First half of CreateRasterMapLayer...", 1)

        finalMapLayer.description = dSDV["attributedescription"] + "\r\n\r\n" + parameterString
        arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
        arcpy.RefreshTOC()

        if arcpy.Exists(outputLayerFile):
            arcpy.Delete_management(outputLayerFile)

        arcpy.SaveToLayerFile_management(finalMapLayer, outputLayerFile)
        PrintMsg("\tSaved map to layer file: " + outputLayerFile + " \n ", 0)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateDummyRaster(classBV):
    # Create a dummy raster file with Unique Value renderer to update the output raster symbology
    #
    #
    #
    try:
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Define filenames and paths
        ascFile = os.path.join(env.scratchFolder, "symraster.asc")
        symLayer = os.path.join(env.scratchFolder, "symraster.lyr")
        symRaster = os.path.join(env.scratchGDB, "symraster")

        # Clean up from previous runs
        if arcpy.Exists(ascFile):
            arcpy.Delete_management(ascFile)

        if arcpy.Exists(symLayer):
            arcpy.Delete_management(symLayer)

        if arcpy.Exists(symRaster):
            arcpy.Delete_management(symRaster)

        # Create ascii raster file
        fh = open(ascFile, "w")
        fh.write("NCOLS 1\n")
        fh.write("NROWS " + str(len(classBV)) + "\n")
        fh.write("XLLCORNER 0\n")
        fh.write("YLLCORNER 0\n")
        fh.write("CELLSIZE 1\n")
        fh.write("NODATA_VALUE -32768\n")
        valList =  [str(i) for i in range(len(classBV))]
        vals = " ".join(valList)
        fh.write(vals)
        fh.close()

        # Create file geodatabase raster
        arcpy.ASCIIToRaster_conversion(ascFile, symRaster, "INTEGER")

        # Add rating field
        theType = dFieldInfo[dSDV["resultcolumnname"].upper()][0]
        dataLen = dFieldInfo[dSDV["resultcolumnname"].upper()][1]
        arcpy.AddField_management(symRaster, dSDV["resultcolumnname"].upper(), theType, "", "", dataLen)

        # Populate rating field

        with arcpy.da.UpdateCursor(symRaster, [dSDV["resultcolumnname"].upper()]) as cur:
            i = 0
            for rec in cur:
                cur.updateRow([classBV[i]])
                i += 1

        # Create temporary raster layer then export to layer file
        arcpy.MakeRasterLayer_management(symRaster, "Sym Raster")
        arcpy.SaveToLayerFile_management("Sym Raster", symLayer)
        arcpy.Delete_management("Sym Raster")


        return symLayer

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def ValidateName(inputName):
    # Remove characters from file name or table name that might cause problems
    try:
        #PrintMsg(" \nValidating input table name: " + inputName, 1)
        f = os.path.basename(inputName)
        db = os.path.dirname(inputName)
        validName = ""
        validChars = "_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        lastChar = "."
        charList = list()

        for s in f:
            if s in validChars:
                if  not (s == "_" and lastChar == "_"):
                    charList.append(s)

                elif lastChar != "_":
                    lastChar = s

        validName = "".join(charList)

        return os.path.join(db, validName)

    except MyError, e:
        PrintMsg(str(e), 2)
        try:
            arcpy.RemoveJoin_management(inputLayer, outputTbl)
            return ""
        except:
            return ""

    except:
        errorMsg()
        try:
            arcpy.RemoveJoin_management(inputLayer, outputTbl)
            return ""

        except:
            return ""

## ===================================================================================
def ReadTable(tbl, flds, wc, level, sql):
    # Read target table using specified fields and optional sql
    # Other parameters will need to be passed or other functions created
    # to handle aggregation methods and tie-handling
    # ReadTable(dSDV["attributetablename"].upper(), flds, primSQL, level, sql)
    try:
        #bVerbose = True

        arcpy.SetProgressorLabel("Reading input data (" + tbl.lower() +")")
        start = time.time()

        # Create dictionary to store data for this table
        dTbl = dict()
        # Open table with cursor
        iCnt = 0

        # ReadTable Diagnostics
        if bVerbose:
            PrintMsg(" \nReading Table: " + tbl + ", Fields: " + str(flds), 1)
            PrintMsg("WhereClause: " + str(wc) + ", SqlClause: " + str(sql) + " \n ", 1)

        with arcpy.da.SearchCursor(tbl, flds, where_clause=wc, sql_clause=sql) as cur:
            for rec in cur:
                #if level == 1:
                #    PrintMsg("\t" + str(rec), 1)
                val = list(rec[1:])

                try:
                    dTbl[rec[0]].append(val)

                except:
                    dTbl[rec[0]] = [val]

                iCnt += 1

        if bVerbose:
            theMsg = " \nProcessed " + Number_Format(iCnt, 0, True) + " " +tbl + " records in " + elapsedTime(start)
            PrintMsg(theMsg, 0)

        return dTbl

    except:
        errorMsg()
        return dict()

## ===================================================================================
def ListMonths():
    # return list of months
    try:
        moList = ['NULL', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        return moList

    except:
        errorMsg()
        return []

## ===================================================================================
def GetAreasymbols(gdb):
    # return a dictionary for AREASYMBOL. Key = LKEY and Value = AREASYMBOL
    #
    try:
        dAreasymbols = dict()

        inputTbl = os.path.join(gdb, "LEGEND")

        # Get list of areasymbols from input feature layer
        #
        # I should probably compare the count of the featureclass vs the count of the featurelayer. If they are the
        # same, then just use the legend and skip this next part. I'm assuming that if the input featureclass name
        # is NOT "MUPOLYGON" then this is a subset and will automatically get the list from the input layer.
        #
        #
        if fcCnt != polyCnt or os.path.basename(fc) != "MUPOLYGON" and dataType != "rasterlayer":
            areasymbolList = list()  # new code
            #PrintMsg(" \nGetting list of areasymbols from the input soils layer", 1)
            #sqlClause = ("DISTINCT", "ORDER BY AREASYMBOL")
            sqlClause = ("DISTINCT", None)

            with arcpy.da.SearchCursor(inputLayer, ["AREASYMBOL"], sql_clause=sqlClause) as cur:  # new code
                for rec in cur:  # new code
                    areasymbolList.append(rec[0].encode('ascii')) # new code

            areasymbolList.sort()
            #PrintMsg(" \nFinished getting list of areasymbols (" + Number_Format(len(areasymbolList), 0, True) + ") for the input soils layer", 1)

            # Now get associated mapunit-legend keys for use in other queries
            #
            if len(areasymbolList) == 1:
                whereClause = "AREASYMBOL = '" + areasymbolList[0] + "'"

            else:
                whereClause = "AREASYMBOL IN " + str(tuple(areasymbolList))

            with arcpy.da.SearchCursor(inputTbl, ["LKEY", "AREASYMBOL"], where_clause=whereClause) as cur:
                for rec in cur:
                    if rec[1] in areasymbolList:  # new code
                        dAreasymbols[rec[0]] = rec[1]

        else:
            # For raster layers, get AREASYMBOL from legend table. Not ideal, but alternatives could be much slower.
            #PrintMsg(" \nGetting list of areasymbols from the input database", 1)

            with arcpy.da.SearchCursor(inputTbl, ["LKEY", "AREASYMBOL"]) as cur:
                for rec in cur:
                    dAreasymbols[rec[0]] = rec[1]

        return dAreasymbols

    except:
        errorMsg()
        return dAreasymbols

## ===================================================================================
def GetSDVAtts(gdb, sdvAtt, aggMethod):
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    try:
        # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        sql1 = "attributename = '" + sdvAtt + "'"

        if bVerbose:
            PrintMsg(" \nReading sdvattribute table into dSDV dictionary", 1)

        with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
            rec = cur.next()  # just reading first record
            i = 0
            for val in rec:
                dSDV[flds[i].lower()] = val
                #PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                i += 1

        # Revise some attributes to accomodate fuzzy number mapping code
        #
        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        #if dSDV["attributetype"].lower() == "interpretation" and (dSDV["nasisrulename"][0:5] == "NCCPI" or bFuzzy == True):
        if dSDV["attributetype"].lower() == "interpretation" and (dSDV["effectivelogicaldatatype"] == "float" or bFuzzy == True):
            #PrintMsg(" \nDo I need to handle both NCCPI versions at this point??", 1)
            dSDV["attributecolumnname"] = "INTERPHR"

            if dSDV["nasisrulename"][0:5] != "NCCPI":
                dSDV["effectivelogicaldatatype"] = 'float'
                dSDV["attributelogicaldatatype"] = 'float'
                dSDV["maplegendkey"] = 3
                dSDV["maplegendclasses"] = 5
                dSDV["attributeprecision"] = 2

        # Temporary workaround for sql whereclause. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = 'UPPER("' + sqlParts[0] + '") = ' + sqlParts[1].upper()

        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False and dSDV["notratedphrase"] is None:
            # Add 'Not rated' to choice list
            dSDV["notratedphrase"] = "Not rated" # should not have to do this, but this is not always set in Rule Manager

        if dSDV["secondaryconcolname"] is not None and dSDV["secondaryconcolname"].lower() == "yldunits":
            # then this would be units for legend (component crop yield)
            #PrintMsg(" \nSetting units of measure to: " + secCst, 1)
            dSDV["attributeuomabbrev"] = secCst

        if dSDV["attributecolumnname"].endswith("_r") and sRV in ["Low", "High"]:
            if sRV == "Low":
                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_l")

            elif sRV == "High":
                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_h")

            #PrintMsg(" \nUsing attribute column " + dSDV["attributecolumnname"], 1)

        if dSDV["tiebreaklowlabel"] is None:
            dSDV["tiebreaklowlabel"] = "Lower"

        if dSDV["tiebreakhighlabel"] is None:
            dSDV["tiebreakhighlabel"] = "Higher"

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            #PrintMsg(" \nUpdating dAgg", 1)
            dAgg["Minimum or Maximum"] = "Max"

        else:
            dAgg["Minimum or Maximum"] = "Min"
            #PrintMsg(" \nUpdating dAgg", 1)

        if dAgg[aggMethod] == "":
            dSDV["resultcolumnname"] = dSDV["resultcolumnname"]

        else:
            dSDV["resultcolumnname"] = dSDV["resultcolumnname"] + "_" + dAgg[aggMethod]

        #PrintMsg(" \nSetting resultcolumn name to: '" + dSDV["resultcolumnname"] + "'", 1)



        return dSDV

    except:
        errorMsg()
        return dSDV

## ===================================================================================
def GetRatingDomain(gdb):
    # return list of tiebreak domain values for rating
    # modify this function to use uppercase string version of values
    #
    # The tiebreak domain name is not always used, even when there is a set
    # of domain names for the attribute (eg Conservation Tree and Shrub Group)

    try:

        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        mdcols = os.path.join(gdb, "mdstatdomdet")
        domainName = dSDV["tiebreakdomainname"]
        #PrintMsg(" \ndomainName: " + str(domainName), 1)
        domainValues = list()

        if dSDV["tiebreakdomainname"] is not None:
            wc = "domainname = '" + dSDV["tiebreakdomainname"] + "'"

            sc = (None, "ORDER BY choicesequence ASC")

            with arcpy.da.SearchCursor(mdcols, ["choice", "choicesequence"], where_clause=wc, sql_clause=sc) as cur:
                for rec in cur:
                    domainValues.append(rec[0])

        elif bVerbose:
            PrintMsg(" \n" + sdvAtt + ": no domain choices found", 1)

        return domainValues

    except:
        errorMsg()
        return []

## ===================================================================================
def GetValuesFromLegend(dLegend):
    # return list of legend values from dLegend (XML source)
    # modify this function to use uppercase string version of values

    try:
        legendValues = list()

        if len(dLegend) > 0:
            pass
            #dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext Now a global


        else:

            PrintMsg(" \nChanging legend name to 'Progressive'", 1)
            PrintMsg(" \ndLegend: " + str(dLegend["name"]), 1)
            legendValues = list()
            dLegend["name"] = "Progressive"  # bFuzzy
            dLegend["type"] = "1"

        labelCnt = len(dLabels)     # get count for number of legend labels in dictionary

        #if not dLegend["name"] in ["Progressive", "Defined"]:
        # Note: excluding defined caused error for Interp DCD (Haul Roads and Log Landings)

        if not dLegend["name"] in ["Progressive", "Defined"]:
            # example AASHTO Group Classification
            legendValues = list()      # create empty list for label values

            for order in range(1, (labelCnt + 1)):
                #legendValues.append(dLabels[order]["value"].title())
                legendValues.append(dLabels[order]["value"])

                if bVerbose:
                    PrintMsg("\tAdded legend value #" + str(order) + " ('" + dLabels[order]["value"] + "') from XML string", 1)

        elif dLegend["name"] == "Defined":
            #if dSDV["attributelogicaldatatype"].lower() in ["string", "choice]:
            # Non-numeric values
            for order in range(1, (labelCnt + 1)):
                try:
                    # Hydric Rating by Map Unit
                    legendValues.append(dLabels[order]["upper_value"])
                    legendValues.append(dLabels[order]["lower_value"])

                except:
                    # Other Defined such as 'Basements With Dwellings', 'Land Capability Class'
                    legendValues.append(dLabels[order]["value"])

        return legendValues

    except:
        errorMsg()
        return []

## ===================================================================================
def CreateInitialTable(gdb, allFields, dFieldInfo):
    # Create the empty output table that will contain key fields from all levels plus
    # the input rating field
    #
    try:
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        initialTbl = "SDV_Data"

        tblLoc = gdb

        if arcpy.Exists(os.path.join(tblLoc, initialTbl)):
            arcpy.Delete_management(os.path.join(tblLoc, initialTbl))

        arcpy.CreateTable_management(tblLoc, initialTbl)

        iFlds = len(allFields)
        newField = dSDV["attributecolumnname"].title()
        i = 0

        # Drop LKEY
        #allFields.remove("LKEY")

        #PrintMsg(" \nRating field (" + resultcolumn + ") set to " + str(dFieldInfo[resultcolumn]), 1)

        # Add required fields to initial table
        i = 0
        for fld in allFields:
            i += 1
            if fld != "LKEY":
                if i == len(allFields):
                    #PrintMsg("\tAdding last field " + fld + " to initialTbl as a " + dFieldInfo[fld][0], 1)
                    #PrintMsg("\tAdding last field RATING to initialTbl as a " + dFieldInfo[fld][0], 1)
                    arcpy.AddField_management(os.path.join(tblLoc, initialTbl), fld.upper(), dFieldInfo[fld][0], "", "", dFieldInfo[fld][1], dSDV["resultcolumnname"].upper())
                    #arcpy.AddField_management(os.path.join(tblLoc, initialTbl), "RATING", dFieldInfo[fld][0], "", "", dFieldInfo[fld][1], "RATING")

                else:
                    #PrintMsg("\tAdding field " + fld + " to initialTbl as a " + dFieldInfo[fld][0], 1)
                    arcpy.AddField_management(os.path.join(tblLoc, initialTbl), fld.upper(), dFieldInfo[fld][0], "", "", dFieldInfo[fld][1])

        return os.path.join(tblLoc, initialTbl)

    except:
        errorMsg()

        return None

## ===================================================================================
def GetMapunitSymbols(gdb):
    # Populate dictionary using mukey and musym
    # This function is for development purposes only and will probably not be
    # used in the final version.

    dSymbols = dict()

    try:

        with arcpy.da.SearchCursor("MAPUNIT", ["MUKEY", "MUSYM"]) as mCur:
            for rec in mCur:
                dSymbols[rec[0]] = rec[1]

        return dSymbols

    except MyError, e:
        PrintMsg(str(e), 2)
        return dSymbols

    except:
        errorMsg()
        return dSymbols

## ===================================================================================
def CreateOutputTable(initialTbl, outputTbl, dFieldInfo):
    # Create the initial output table that will contain key fields from all levels plus the input rating field
    #
    try:
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Validate output table name
        outputTbl = ValidateName(outputTbl)

        if outputTbl == "":
            return ""

        # Delete table from prior runs
        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        # Create the final output table using initialTbl as a template
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl), initialTbl)

        # Drop the last column which should be 'attributecolumname' and replace with 'resultcolumname'
        #lastFld = dSDV["attributecolumnname"]
        arcpy.DeleteField_management(outputTbl, dSDV["attributecolumnname"])
        arcpy.DeleteField_management(outputTbl, "MUSYM")
        arcpy.DeleteField_management(outputTbl, "COMPNAME")
        if dSDV["resultcolumnname"].upper() != "MUNAME":
            arcpy.DeleteField_management(outputTbl, "MUNAME")

        # Drop COKEY and CHKEY if present
        fldList = arcpy.Describe(outputTbl).fields

        for fld in fldList:
            if fld.name.upper() in ["COKEY", "CHKEY", "HZDEPT_R", "HZDEPB_R", "COMONTHKEY", "LKEY"]:
                arcpy.DeleteField_management(outputTbl, fld.name)

        #fieldName = dSDV[resultcolumn]
        theType = dFieldInfo[dSDV["resultcolumnname"].upper()][0]
        dataLen = dFieldInfo[dSDV["resultcolumnname"].upper()][1]
        # arcpy.AddField_management(outputTbl, dSDV["resultcolumnname"].upper(), theType, "", "", dataLen, outputLayer)
        arcpy.AddField_management(outputTbl, dSDV["resultcolumnname"].upper(), theType, "", "", dataLen)

        arcpy.AddIndex_management(outputTbl, "MUKEY", "Indx" + os.path.basename(outputTbl))

        if arcpy.Exists(outputTbl):
            return outputTbl

        else:
            raise MyError, "Failed to create output table"

    except MyError, e:
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def CreateRatingTable1(tblList, sdvTbl, initialTbl, dAreasymbols):
    # Create level 1 table (mapunit only)
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Remove LKEY from allFields - kludge
        allFields.remove("LKEY")

        # Read mapunit table and populate initial table
        #PrintMsg(" \nUsing input fields: " + ", ".join(dFields["MAPUNIT"]), 1)

        with arcpy.da.SearchCursor(os.path.join(gdb, "mapunit"), dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:

            # MUNAME is rating field
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                if len(dFields["MAPUNIT"]) == 4:
                    for rec in mCur:
                        mukey, musym, muname, lkey = rec

                        #if lkey in dAreasymbols: # new code
                        try:
                            murec = [dAreasymbols[lkey], mukey, musym, muname]
                            #PrintMsg("\t" + str(murec), 1)
                            ocur.insertRow(murec)

                        except:
                            pass

                elif len(dFields["MAPUNIT"]) == 5:
                # rating field is not MUNAME
                    for rec in mCur:
                        mukey, musym, muname, lkey, rating = rec

                        try: # new code
                            murec = [dAreasymbols[lkey], mukey, musym, muname, rating]
                            #PrintMsg("\t" + str(murec), 1)
                            ocur.insertRow(murec)

                        except:
                            pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable1S(tblList, sdvTbl, dTbl, initialTbl, dAreasymbols):
    # Create level 2 table (mapunit, sdvTbl)
    #

    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec
                    #PrintMsg("\t" + str(rec), 1)

                    try:
                        sdvrecs = dTbl[mukey]

                        for sdvrec in sdvrecs:

                            try:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(sdvrec)
                                ocur.insertRow(newrec)

                            except:
                                pass

                    except:

                        try: # new code
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing[sdvTbl])
                            ocur.insertRow(newrec)

                        except:
                            pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable3(tblList, sdvTbl, dComponent, dHorizon, initialTbl):
    # Populate level 3 table (mapunit, component, chorizon)
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        #PrintMsg(" \nUsing mapunit fields: " + ", ".join(dFields["MAPUNIT"]), 1)
        #PrintMsg(" \nUsing initial table fields: " + ", ".join(allFields), 1)

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    #if lkey in dAreasymbols: # new code
                    try:
                        newrec = [dAreasymbols[lkey], mukey, musym, muname]

                        try:
                            corecs = dComponent[mukey]

                            for corec in corecs:
                                try:
                                    chrecs = dHorizon[corec[0]]

                                    for chrec in chrecs:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(chrec)
                                        #PrintMsg("\t" + str(newrec), 1)
                                        ocur.insertRow(newrec)

                                except:
                                    # No chorizon records
                                    newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                    newrec.extend(corec)
                                    newrec.extend(dMissing["CHORIZON"])
                                    #PrintMsg("\t" + str(newrec), 1)
                                    ocur.insertRow(newrec)

                        except:
                            try: # new code
                                # No component records, chorizon records
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(dMissing["COMPONENT"])
                                newrec.extend(dMissing["CHORIZON"])
                                #PrintMsg("\t" + str(newrec), 1)
                                ocur.insertRow(newrec)

                            except:
                                pass

                    except:
                        pass

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable2(tblList, sdvTbl, dComponent, initialTbl):
    # Create table using (mapunit, component) where rating is in the component table
    #
    # This works as of 2016-02-13, incorporating AREASYMBOL

    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        if bVerbose:
            PrintMsg(" \nUsing mapunit fields: " + ", ".join(dFields["MAPUNIT"]), 1)
            PrintMsg("Using initial table fields: " + ", ".join(allFields), 1)
            PrintMsg("Using query: " + str(dSQL["MAPUNIT"]) + " \n", 1)
            PrintMsg(" \nOutput table: " + os.path.basename(initialTbl), 1)
            PrintMsg(" \n" + ", ".join(allFields) + " \n ", 1)
            PrintMsg(80 * "=", 1)

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec
                    #if lkey in dAreasymbols: # new code
                    try:

                        try:
                            corecs = dComponent[mukey]

                            for corec in corecs:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(corec)
                                #PrintMsg(str(newrec), 1)
                                ocur.insertRow(newrec)

                        except:
                            # No component records
                            try:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(dMissing["COMPONENT"])
                                #PrintMsg(str(newrec), 1)
                                ocur.insertRow(newrec)

                            except:
                                pass

                    except:
                        pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable2S(tblList, sdvTbl, dComponent, dTbl, initialTbl):
    # Create level 2 table (mapunit, component, sdvTbl)
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        #PrintMsg(" \nCreateRatingTable2S", 1)
        sqlClause = (None, "ORDER BY " + dSDV["resultcolumnname"].upper() + " DESC")  # original

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec
                    #if lkey in dAreasymbols: # new code
                    try:

                        try:
                            corecs = dComponent[mukey]

                            for corec in corecs:

                                try:
                                    sdvrecs = dTbl[corec[0]]

                                    for sdvrec in sdvrecs:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(sdvrec)
                                        #PrintMsg("\t" + str(newrec), 1)
                                        ocur.insertRow(newrec)

                                except:
                                    # No rating value
                                    newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                    newrec.extend(corec)
                                    newrec.extend(dMissing[sdvTbl])
                                    #PrintMsg("\t" + str(newrec) + "***", 1)
                                    ocur.insertRow(newrec)

                        except:
                            # No component records
                            try:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(dMissing["COMPONENT"])
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg("\t" + str(newrec), 1)
                                ocur.insertRow(newrec)

                            except:
                                pass

                    except:
                        pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingInterps(tblList, sdvTbl, dComponent, dTbl, initialTbl):
    #
    # Populate table for standard interp using (mapunit, component, cointerp)
    #
    #PrintMsg(" \nTry improving performance by adding an attribute index to cointerp.mrulename column", 1)
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read all reccords from mapunit table
        allFields.remove("LKEY")

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:

            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    try:
                        corecs = dComponent[mukey]

                        for corec in corecs:

                            try:
                                sdvrecs = dTbl[corec[0]]

                                for sdvrec in sdvrecs:
                                    newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                    newrec.extend(corec)
                                    newrec.extend(sdvrec)
                                    #PrintMsg(str(newrec), 1)
                                    ocur.insertRow(newrec)

                            except:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(corec)
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg(str(newrec), 1)
                                ocur.insertRow(newrec)

                    except:
                        # No component record
                        try:
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing["COMPONENT"])
                            newrec.extend(dMissing[sdvTbl])
                            #PrintMsg(str(newrec), 1)
                            ocur.insertRow(newrec)

                        except:
                            pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable3S(tblList, sdvTbl, dComponent, dHorizon, dTbl, initialTbl):
    # Create level 4 table (mapunit, component, chorizon, sdvTbl)
    # This is set up for surface texture. Is it called by others?
    #
    # At some point may want to look at returning top mineral horizon instead of hzdept_r = 0.
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        #PrintMsg(" \nRunning CreateRatingTable3S for ?Surface Texture?... \n ", 1)

        if not sdvAtt in ["AASHTO Group Classification (Surface)", "Surface Texture", "Unified Soil Classification (Surface)"]:
            raise MyError, "CreateRatingTable3S cannot handle " + sdvAtt + " option"

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:

                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    try:
                        corecs = dComponent[mukey]

                        for corec in corecs:

                            try:
                                hzrecs = dHorizon[corec[0]]

                                for hzrec in hzrecs:
                                    try:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        sdvrec = dTbl[hzrec[0]][0]
                                        newrec.extend(corec)
                                        newrec.extend(hzrec)

                                        # Important note: in this next line I am only retrieving the first
                                        # horizon value from a list. This would be the rating for the top of the
                                        # specified depth range.
                                        #
                                        newrec.extend(sdvrec)  # save only rating for first horizon
                                        #PrintMsg("\t" + str(newrec), 0)
                                        ocur.insertRow(newrec)

                                    except:
                                        # missing sdv rating value
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(hzrec)
                                        newrec.extend(dMissing[sdvTbl])
                                        #PrintMsg("\t" + str(newrec) + "******", 1)
                                        ocur.insertRow(newrec)

                            except:
                                # missing horizon data
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(corec)
                                newrec.extend(dMissing["CHORIZON"])
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg("\t" + str(newrec), 1)
                                ocur.insertRow(newrec)

                    except:
                        # No component, horizon or sdv records
                        try:
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing["COMPONENT"])
                            newrec.extend(dMissing["CHORIZON"])
                            newrec.extend(dMissing[sdvTbl])
                            #PrintMsg("\t" + str(newrec), 1)
                            ocur.insertRow(newrec)

                        except:
                            # Skip missing mapunits (outside AOI)
                            pass
        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateRatingTable4S(tblList, sdvTbl, dComponent, dHorizon, dTbl, initialTbl):
    # Create level 3 table (mapunit, component, horizon)
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        # Read mapunit table
        allFields.remove("LKEY")

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    try:
                        corecs = dComponent[mukey]

                        for corec in corecs:

                            try:
                                #sdvrecs = dTbl[corec[0]]
                                hzrecs = dHorizon[corec[0]]

                                for hzrec in hzrecs:
                                    try:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        sdvrecs = dTbl[hzrec[0]]
                                        newrec.extend(corec)
                                        newrec.extend(hzrec)
                                        newrec.extend(dTbl[hzrec[0]])
                                        #PrintMsg("\t" + str(newrec), 1)
                                        ocur.insertRow(newrec)

                                    except:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(hzrec)
                                        newrec.extend(dMissing[sdvTbl])
                                        #PrintMsg("\t" + str(newrec), 1)
                                        ocur.insertRow(newrec)

                            except:
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend("COMPONENT")
                                newrec.extend("CHORIZON")
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg("\t" + str(newrec), 1)
                                ocur.insertRow(newrec)

                    except:
                        # No component records
                        try:
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing["COMPONENT"])
                            newrec.extend(dMissing[sdvTbl])
                            #PrintMsg("\t" + str(newrec), 1)
                            ocur.insertRow(newrec)

                        except:
                            pass

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSoilMoistureTable(tblList, sdvTbl, dComponent, dMonth, dTbl, initialTbl, begMo, endMo):
    # Create level 4 table (mapunit, component, cmonth, cosoilmoist)
    #
    # Problem 2017-07-24 Steve Campbell found Yolo County mapunits where dominant component,
    # Depth to Water Table map is reporting 201cm for 459272 where the correctg result should be 91cm.
    # My guess is that because there are some months in COSOILMOIST table that are Null, this function
    # is using that value instead of the other months that are 91cm. Try removing NULLs in query that
    # creates the SDV_Data table.
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg

        #
        # Read mapunit table and then populate the initial output table
        allFields.remove("LKEY")

        with arcpy.da.SearchCursor("MAPUNIT", dFields["MAPUNIT"], sql_clause=dSQL["MAPUNIT"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    try:
                        newrec = list()
                        corecs = dComponent[mukey]

                        for corec in corecs:

                            try:
                                newrec = list()
                                morecs = dMonth[corec[0]]

                                for morec in morecs:
                                    try:
                                        sdvrecs = dTbl[morec[0]]

                                        for sdvrec in sdvrecs:
                                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                            newrec.extend(corec)
                                            newrec.extend(morec)
                                            newrec.extend(sdvrec)
                                            #PrintMsg("\t1. " + str(newrec), 1)
                                            ocur.insertRow(newrec)

                                    except:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(morec)
                                        newrec.extend(dMissing[sdvTbl])
                                        #PrintMsg("\t2. " + str(newrec), 1)
                                        ocur.insertRow(newrec)

                            except:
                                # No comonth records
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(corec)
                                newrec.extend(dMissing["COMONTH"])
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg("\t3. " + str(newrec), 1)
                                ocur.insertRow(newrec)

                    except:
                        # No component records or comonth records
                        try:
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing["COMPONENT"])
                            newrec.extend(dMissing["COMONTH"])
                            newrec.extend(dMissing[sdvTbl])
                            #PrintMsg("\t4. " + str(newrec), 1)
                            ocur.insertRow(newrec)

                        except:
                            pass

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def Aggregate1(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate map unit level table
    # Added Areasymbol to output
    try:
        arcpy.SetProgressorLabel("Assembling map unit level data")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Read mapunit table and populate final output table
        # Create final output table with MUKEY and sdvFld
        #
        # Really no difference between the two tables, so this
        # is redundant. Should fix this later after everything
        # else is working.
        #
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()
        inFlds = ["MUKEY", "AREASYMBOL", dSDV["attributecolumnname"].upper()]
        outFlds = ["MUKEY", "AREASYMBOL", dSDV["resultcolumnname"].upper()]
        outputValues = list()

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        fldPrecision = max(0, dSDV["attributeprecision"])

        if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
            # populate sdv_initial table and create list of min-max values
            iMax = -999999999
            iMin = 999999999

            with arcpy.da.SearchCursor(initialTbl, inFlds) as cur:
                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, val = rec

                        if not val is None:
                            val = round(val, fldPrecision)

                        iMax = max(val, iMax)

                        if not val is None:
                            iMin = min(val, iMin)

                        rec = [mukey, areasym, val]
                        ocur.insertRow(rec)

            # add max and min values to list
            outputValues = [iMin, iMax]

            if iMin == None and iMax == -999999999:
                # No data
                raise MyError, "No data for " + sdvAtt

        else:
            # populate sdv_initial table and create a list of unique values
            with arcpy.da.SearchCursor(initialTbl, inFlds) as cur:
                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, val = rec
                        if not val in outputValues:
                            outputValues.append(val)

                        ocur.insertRow(rec)

        if len(outputValues) < 20 and bVerbose:
            PrintMsg(" \nInitial output values: " + str(outputValues), 1)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component data to the map unit level using dominant component
    # Added areasymbol to output
    try:
        #bVerbose = True
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        outputValues = list()

        inFlds = ["MUKEY", "AREASYMBOL", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper()]
        outFlds = ["MUKEY", "AREASYMBOL", "COMPPCT_R", dSDV["resultcolumnname"].upper()]

        #PrintMsg(" \ntieBreaker in AggregateCo_DCD is: " + tieBreaker, 1)
        #PrintMsg(str(dSDV["tiebreaklowlabel"]) + "; " + str(dSDV["tiebreakhighlabel"]), 1)


        if tieBreaker == dSDV["tiebreaklowlabel"]:
            sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"].upper() + " ASC ")
            #PrintMsg(" \nAscending sort on " + dSDV["attributecolumnname"], 1)

        else:
            sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"].upper() + " DESC ")
            #PrintMsg(" \nDescending sort on " + dSDV["attributecolumnname"], 1)


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            raise MyError, "No output table"
            return outputTbl, outputValues

        lastMukey = "xxxx"

        # Reading numeric data from initial table
        #
        if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
            #PrintMsg(" \nEffectiveLogicalDataType: " + dSDV["effectivelogicaldatatype"].lower(), 1)
            # populate sdv_initial table and create list of min-max values
            iMax = -999999999.0
            iMin = 999999999.0
            fldPrecision = max(0, dSDV["attributeprecision"])

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause) as cur:

                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, cokey, comppct, rating = rec

                        if mukey != lastMukey and lastMukey != "xxxx":

                            if not rating is None:
                                newrec = mukey, areasym, comppct, round(rating, fldPrecision)

                            else:
                                newrec = mukey, areasym, comppct, None

                            ocur.insertRow(newrec) # Error here. sequence size.

                            if not rating is None:
                                iMax = max(rating, iMax)

                                if not rating is None:
                                    iMin = min(rating, iMin)

                        lastMukey = mukey

            # add max and min values to list
            outputValues = [iMin, iMax]

        else:
            # For text, vtext or choice data types
            #
            #PrintMsg(" \ndValues: " + str(dValues), 1)
            #PrintMsg(" \noutputValues: " + str(outputValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause) as cur:

                if len(dValues) > 0:
                    # Text, has domain values or values in the maplegendxml
                    #
                    with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                        for rec in cur:

                            mukey, areasym, cokey, comppct, rating = rec

                            if mukey != lastMukey:

                                #if not rating is None:
                                if str(rating).upper() in dValues:
                                    if dValues[rating.upper()][1] != rating: # we have a case problem in the maplegendxml
                                        # switch the dValue to lowercase to match the data
                                        dValues[str(rating).upper()][1] = rating

                                    newrec = [mukey, areasym, comppct, rating]

                                elif not rating is None:

                                    dValues[str(rating).upper()] = [None, rating]
                                    newrec = [mukey, areasym, comppct, rating]

                                else:
                                    newrec = [mukey, areasym, None, None]

                                if not rating in outputValues and not rating is None:
                                    outputValues.append(rating)

                                ocur.insertRow(newrec)
                                #PrintMsg(str(rec), 1)

                            lastMukey = mukey

                else:
                    # Text, without domain values
                    #
                    with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                        for rec in cur:
                            mukey, areasym, cokey, comppct, rating = rec

                            if mukey != lastMukey:
                                if not rating is None:
                                    newVal = rating.strip()

                                else:
                                    newVal = None

                                ocur.insertRow([mukey, areasym, comppct, newVal])

                                #if mukey == '536847':
                                #    PrintMsg(str([mukey, areasym, comppct, newVal]), 1)
                                #PrintMsg("\tWriting " + str([rec[0], rec[2], newVal]), 0)

                                if not newVal is None and not newVal in outputValues:
                                    outputValues.append(newVal)

                            #else:
                            #    PrintMsg("\tSkipping " + str(rec), 1)

                            lastMukey = mukey


        if None in outputValues:
            outputValues.remove(None)

        if outputValues[0] == 999999999.0 or outputValues[1] == -999999999.0:
            # Sometimes no data can skip through the max min test
            outputValues = [0.0, 0.0]
            raise MyError, "No data for " + sdvAtt

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        # Trying to handle NCCPI for dominant component
        if dSDV["attributetype"].lower() == "interpretation" and (dSDV["nasisrulename"][0:5] == "NCCPI"):
            outputValues = [0.0, 1.0]

        if dSDV["effectivelogicaldatatype"].lower() in ("float", "integer"):
            outputValues.sort()
            return outputTbl, outputValues

        else:
            return outputTbl, sorted(outputValues, key=lambda s: s.lower())

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Limiting(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Select either the "Least Limiting" or "Most Limiting" rating from all components
    # Component aggregation to the maximum or minimum value for the mapunit.

    # Based upon AggregateCo_DCD function, but sorted on rating or domain value instead of comppct
    #
    # domain: soil_erodibility_factor (text)  range = .02 .. .64
    # Added Areasymbol to output

    # Note! I have some dead code for 'no domain values'. Need to delete if those sections are never used.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg(" \nEffective Logical data type: " + dSDV["effectivelogicaldatatype"], 1)
            PrintMsg(" \nAttribute type: " + dSDV["attributetype"] + "; bFuzzy " + str(bFuzzy), 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "AREASYMBOL", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper()]
        outFlds = ["MUKEY", "AREASYMBOL", "COMPPCT_R", dSDV["resultcolumnname"].upper()]

        # ignore any null values
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        #
        sqlClause =  (None, " ORDER BY MUKEY ASC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        if not dSDV["notratedphrase"] is None:
            # This should be for most interpretations
            notRatedIndex = domainValues.index(dSDV["notratedphrase"])

        else:
            # set notRatedIndex for properties that are not interpretations
            notRatedIndex = -1

        # 1. For ratings that have domain values, read data from initial table
        #
        if len(domainValues) > 0:
            #PrintMsg(" \ndValues: " + str(dValues), 1)

            # Save the rating for each component along with a list of components for each mapunit
            #
            try:
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    # inFlds: 0 mukey, 1 cokey, 2 comppct, 3 rating

                    for rec in cur:
                        #PrintMsg(str(rec), 1)
                        mukey, areasym, cokey, comppct, rating = rec
                        dAreasym[mukey] = areasym

                        # Save the associated domain index for this rating
                        dComp[cokey] = dValues[str(rating).upper()][0]

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit using mukey as key
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        #PrintMsg("Component '" + rec[1] + "' at " + str(rec[2]) + "% has a rating of: " + str(rec[3]), 1)

            except:
                errorMsg()

        else:
            # 2. No Domain Values, read data from initial table. Use alpha sort for tiebreaker
            #
            raise MyError, "No Domain values"


        # Write aggregated data to output table

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if aggMethod == "Least Limiting":
                #
                # Need to take a closer look at how 'Not rated' components are handled in 'Least Limiting'
                #
                if domainValues:

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        muVals = list()    # may not need this for DCD
                        #maxIndx = 0        # Initialize index as zero ('Not rated')
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            indexes.append(ratingIndx)
                            #PrintMsg("\t\t" + mukey + ": " + cokey + " - " + str(ratingIndx) + ",  " + domainValues[ratingIndx], 1)

                            if ratingIndx in dRating:
                                 dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        # Use the highest index value to assign the map unit rating
                        indexes = sorted(set(indexes), reverse=True)
                        maxIndx = indexes[0]  # get the lowest index value

                        if maxIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            maxIndx = indexes[1]

                        pct = dRating[maxIndx]
                        rating = domainValues[maxIndx]
                        areasym = dAreasym[mukey]
                        newrec = [mukey, areasym, pct, rating]
                        ocur.insertRow(newrec)
                        #PrintMsg("\tMapunit rating: " + str(indexes) + "; " + str(maxIndx) + "; " + rating + " \n ", 1)

                        if not rating in outputValues:
                            outputValues.append(rating)

                else:
                    # Least Limiting, no domain values
                    #
                    raise MyError, "No domain values"


            elif aggMethod == "Most Limiting":
                #
                # with domain values...
                #
                # Need to take a closer look at how 'Not rated' components are handled in 'Most Limiting'
                #
                if len(domainValues) > 0:
                    #
                    # Most Limiting, has domain values
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes))
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)

                        if not domainValues[minIndx] in outputValues:
                            outputValues.append(domainValues[minIndx])

                else:
                    #
                    # Most Limiting, no domain values
                    raise MyError, "No domain values"

                    #PrintMsg(" \nTesting " + aggMethod + ", no domain values!!!", 1)
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            ratingIndx = dComp[cokey]  # component rating

                            if ratingIndx != 0:
                                if ratingIndx in dRating:
                                    dRating[ratingIndx] = dRating[ratingIndx] + compPct

                                else:
                                    dRating[ratingIndx] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)
                            #PrintMsg("\t" + mukey + ": " + ",  " + str(muVals), 1)

                        if not newrec[2] in outputValues:
                            outputValues.append(newrec[2])

                # End of Lower

        outputValues.sort()

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_MaxMin(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Looks at all components and returns the lowest or highest rating value. This
    # may be based upon the actual value or the index (for those properties with domains).
    #
    # "Minimum or Maximum" method of aggregation uses the tiebreak setting
    # and returns the highest or lowest rating accordingly.

    # "Least Limiting", "Most Limiting"
    # Component aggregation to the maximum or minimum value for the mapunit.
    #
    # dSDV["tiebreakrule"]: -1, 1 originally in sdvattribute table
    #
    # If tieBreak value == "lower" return the minimum value for the mapunit
    # Else return "Higher" value for the mapunit
    #
    # Based upon AggregateCo_DCD function, but sorted on rating or domain value instead of comppct
    #
    # domain: soil_erodibility_factor (text)  range = .02 .. .64
    # Added Areasymbol to output

    try:
        #bVerbose = True

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        if bVerbose:
            PrintMsg(" \nEffective Logical data type: " + dSDV["effectivelogicaldatatype"], 1)
            PrintMsg(" \nAttribute type: " + dSDV["attributetype"] + "; bFuzzy " + str(bFuzzy), 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "AREASYMBOL", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper()]
        outFlds = ["MUKEY", "AREASYMBOL", "COMPPCT_R", dSDV["resultcolumnname"].upper()]

        # ignore any null values
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attributecolumn when it will be replaced by Domain values later?
        #
        if tieBreaker == dSDV["tiebreaklowlabel"]:
            sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"].upper() + " ASC ")

        else:
            sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"].upper() + " DESC ")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        if not dSDV["notratedphrase"] is None:
            # This should work for most interpretations
            if dSDV["notratedphrase"] in domainValues:
                notRatedIndex = domainValues.index(dSDV["notratedphrase"])

            else:
                notRatedIndex = -1

        else:
            # set notRatedIndex for properties that are not interpretations
            notRatedIndex = -1

        #
        # Begin component level processing. Branch according to whether values are members of a domain.
        #
        if len(domainValues) > 0:
            # Save the rating for each component along with a list of components for each mapunit
            #
            try:
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    # inFlds: 0 mukey, 1 cokey, 2 comppct, 3 rating

                    for rec in cur:
                        #PrintMsg(str(rec), 1)
                        mukey, areasym, cokey, comppct, rating = rec
                        dAreasym[mukey] = areasym

                        # Save the associated domain index for this rating
                        dComp[cokey] = dValues[str(rating).upper()][0]

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit using mukey as key
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        #PrintMsg("Component '" + rec[1] + "' at " + str(rec[2]) + "% has a rating of: " + str(rec[3]), 1)

            except:
                errorMsg()

        else:
            # 2. No Domain Values, read data from initial table. Use alpha sort for tiebreaker.
            #
            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    mukey, areasym, cokey, comppct, rating = rec
                    dAreasym[mukey] = areasym
                    # Assume that this is the first rating for the component
                    dComp[cokey] = rating

                    # save component percent for each component
                    dCompPct[cokey] = comppct

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        # End of component level processing
        #


        #
        # Begin process of writing mapunit-aggregated data to output table
        # Branch according to aggregation method and tiebreak settings and whether ratings are members of a domain
        #
        if bVerbose:
            PrintMsg(" \nTieBreaker: " + str(tieBreaker), 1)
            PrintMsg("Tiebreak label: " + str(dSDV["tiebreakhighlabel"]), 1)
            PrintMsg("Tiebreak Rule: " + str(dSDV["tiebreakrule"]), 1)
            PrintMsg("domainValues: " + str(domainValues), 1)
            PrintMsg("notRatedIndex: " + str(notRatedIndex), 1)

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            #
            # Begin Minimum or Maximum
            #
            if aggMethod == "Minimum or Maximum" and tieBreaker == dSDV["tiebreaklowlabel"]:
                #
                # MIN
                #
                if len(domainValues) > 0:
                    #
                    # MIN
                    # Has Domain
                    #
                    #PrintMsg(" \nThis option has domain values for MinMax!", 1) example WEI MaxMin

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes), reverse=False)
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)
                        #PrintMsg("\tPessimistic 3 Mapunit rating: " + str(indexes) + ", " + str(minIndx) + ", " + str(domainValues[minIndx]) + " \n ", 1)

                        if not domainValues[minIndx] in outputValues and not domainValues[minIndx] is None:
                            outputValues.append(domainValues[minIndx])

                else:
                    #
                    # MIN
                    # No domain
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            ratingIndx = dComp[cokey]  # component rating

                            if ratingIndx != 0:
                                if ratingIndx in dRating:
                                    dRating[ratingIndx] = dRating[ratingIndx] + compPct

                                else:
                                    dRating[ratingIndx] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals, 1, 0, False, True)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)
                            #PrintMsg("\t" + mukey + ": " + str(muVal) + " <- " + str(muVals), 1)

                        if not muVal[1] in outputValues and not muVal[1] is None:
                            outputValues.append(muVal[1])

                # End of Lower

            elif aggMethod == "Minimum or Maximum" and tieBreaker == dSDV["tiebreakhighlabel"]:
                #
                # MAX
                #
                if len(domainValues) > 0:
                    #
                    # MAX
                    # Has Domain
                    #
                    #PrintMsg(" \nThis option has domain values for MinMax!", 1)

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes), reverse=True)
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)
                        #PrintMsg("\tOptimistic 3 Mapunit rating: " + str(indexes) + ", " + str(minIndx) + ", " + str(domainValues[minIndx]) + " \n ", 1)

                        if not domainValues[minIndx] in outputValues and not domainValues[minIndx] is None:
                            outputValues.append(domainValues[minIndx])

                else:
                    #raise MyError, "Should not be in this section of code"

                    #PrintMsg(" \nTesting " + aggMethod + " - " + tieBreaker + ", no domain values", 1)
                    #
                    # MAX
                    # No Domain

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            rating = dComp[cokey]  # component rating

                            if rating != 0:
                                if rating in dRating:
                                    dRating[rating] = dRating[rating] + compPct

                                else:
                                    dRating[rating] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals, 1, 0, True, True)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)
                            # muVal[0] is comppct, muVal[1] is rating
                            #PrintMsg("\tThis mapunit " + mukey + " is rated: " + str(muVal[1]) + " <- " + str(muVals), 1)

                        if not muVal[1] in outputValues and not muVal[1] is None:
                            outputValues.append(muVal[1])

                # End of Higher


        outputValues.sort()

        if bVerbose:
            PrintMsg(" \noutputValues: " + str(outputValues), 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCD(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Component aggregation to the dominant condition for the mapunit.
    #
    # Need to remove references to domain values for rating
    #
    # Need to figure out how to handle tiebreaker code for Random values (no index for ratings)
    # Added areasymbol to output
    try:
        #bVerbose = True
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        # ignore any null values
        if not bNulls:
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        else:
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        if bVerbose:
            PrintMsg(" \nwhereClause: " + whereClause, 1)

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        #PrintMsg(" \nMap legend key: " + str(dSDV["maplegendkey"]), 1)
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        # 1 Read initial table (ratings have domain values and can be ranked)
        #

        if len(dValues) and not dSDV["tiebreakdomainname"] is None:
            if bNulls and not "NONE" in dValues:
                # Add Null value to domain
                dValues["NONE"] = [[len(dValues), None]]
                domainValues.append("NONE")

                if bVerbose:
                    PrintMsg(" \nDomain Values: " + str(domainValues), 1)
                    PrintMsg("dValues: " + str(dValues), 1)
                    PrintMsg("data type: " + dSDV["effectivelogicaldatatype"].lower(), 1 )
            #PrintMsg("dValues: " + str(dValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                # Use tiebreak rules and rating index values

                for rec in cur:
                    # read raw data from initial table
                    mukey, cokey, comppct, rating, areasym = rec
                    dRating = dict()

                    # get index for this rating
                    ratingIndx = dValues[str(rating).upper()][0]
                    #PrintMsg("\t" + str(dValues[str(rating).upper()]), 1)
                    dComp[cokey] = ratingIndx
                    dCompPct[cokey] = comppct
                    dAreasym[mukey] = areasym

                    # summarize the comppct for this rating and map unit combination
                    try:
                        dRating[ratingIndx] += comppct
                        #comppct = dRating[ratingIndx]

                    except:
                        dRating[ratingIndx] = comppct

                        #dRating[ratingIndx] = comppct

                    # Not sure what I am doing here???
                    try:
                        #dMapunit[mukey][ratingIndx] = dRating[ratingIndx]
                        dMapunit[mukey].append(cokey)

                    except:
                        #dMapunit[mukey].append(ratingIndx)
                        dMapunit[mukey] = [cokey]

        else:
            # No domain values
            # 2 Read initial table (no domain values, must use alpha sort for tiebreaker)
            # Issue noted by ?? that without tiebreaking method, inconsistent results may occur
            #
            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                #
                # numeric values
                if dSDV["effectivelogicaldatatype"].lower() in ['integer', 'float']:
                    fldPrecision = max(0, dSDV["attributeprecision"])

                    for rec in cur:
                        mukey, cokey, comppct, rating, areasym = rec
                        # Assume that this is the rating for the component
                        # PrintMsg("\t" + str(rec[1]) + ": " + str(rec[3]), 1)
                        dComp[cokey] = rating
                        dAreasym[mukey] = areasym

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit
                        # key value is mukey; dictionary value is a list of cokeys
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                else:
                    #
                    # choice, text, vtext values
                    for rec in cur:
                        # Assume that this is the rating for the component
                        # ConsTreeShrub is good to this point
                        #PrintMsg("\t" + str(rec[1]) + ": " + str(rec[3]), 1)
                        mukey, cokey, comppct, rating, areasym = rec
                        dComp[cokey] = rating.strip()

                        # save component percent for each component
                        dCompPct[cokey] = comppct
                        dAreasym[mukey] = areasym

                        # save list of components for each mapunit
                        # key value is mukey; dictionary value is a list of cokeys
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

        # Aggregate component-level data to the map unit
        #
        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper()]

            #PrintMsg(" \nTiebreak Rule: " + tieBreaker, 1)
            # Using domain values and tiebreaker is DCD Lower
            #
            # Should be using AggregateCo_DCD_Domain instead of these next two
            # Skip them by changing tiebreakrule test to 9999


            #PrintMsg(" \ntieBreaker in AggregateCo_DCD is: " + tieBreaker, 1)
            #PrintMsg(str(dSDV["tiebreaklowlabel"]) + "; " + str(dSDV["tiebreakhighlabel"]), 1)


            if tieBreaker == dSDV["tiebreaklowlabel"]:
                #
                # No domain values, Lower
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    areasym = dAreasym[mukey]

                    for cokey in cokeys:
                        compPct = dCompPct[cokey]
                        rating = dComp[cokey]

                        if rating in dRating:
                            sumPct = dRating[rating] + compPct
                            dRating[rating] = sumPct  # this part could be compacted

                        else:
                            dRating[rating] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    muVal = SortData(muVals, 0, 1, True, False)  # switched from True, False


                    #if mukey == "536847":
                    #    PrintMsg(" \n1. " + tieBreaker + " vals for: " + mukey + ": " + str(muVals), 1)
                    #    PrintMsg("\tSelected " + str(muVal) + " from " + str(muVals), 1)


                    newrec = [mukey, muVal[0], muVal[1], areasym]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

            elif tieBreaker == dSDV["tiebreakhighlabel"]:
                #
                # No domain values, Higher
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    areasym = dAreasym[mukey]

                    for cokey in cokeys:
                        compPct = dCompPct[cokey]
                        rating = dComp[cokey]

                        if rating in dRating:
                            sumPct = dRating[rating] + compPct
                            dRating[rating] = sumPct  # this part could be compacted

                        else:
                            dRating[rating] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    muVal = SortData(muVals, 0, 1, True, True)  # switched from True, True
                    newrec = [mukey, muVal[0], muVal[1], areasym]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

            else:
                raise MyError, "Failed to aggregate map unit data"

        outputValues.sort()

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        # Problem with integer or float data below

        if dSDV["effectivelogicaldatatype"].lower() in ['integer', 'float']:

            for rating in outputValues:
                #PrintMsg(" \ndValues for " + rating.upper() + ": " + str(dValues[rating.upper()][1]), 1)

                if rating in dValues:
                    # rating is in dValues but case is wrong
                    # fix dValues value
                    #PrintMsg("\tChanging dValue rating to: " + rating, 1)
                    dValues[rating][1] = rating

        else:
            for rating in outputValues:
                #PrintMsg(" \ndValues for " + rating.upper() + ": " + str(dValues[rating.upper()][1]), 1)

                if rating.upper() in dValues and dValues[rating.upper()][1] != rating:
                    # rating is in dValues but case is wrong
                    # fix dValues value
                    #PrintMsg("\tChanging dValue rating to: " + rating, 1)
                    dValues[rating.upper()][1] = rating


        #PrintMsg(" \ndValues (after) in AggregateCo_DCD: " + str(dValues), 1)

        if dSDV["effectivelogicaldatatype"].lower() in ["float", "integer"]:
            return outputTbl, outputValues

        else:
            return outputTbl, sorted(outputValues, key=lambda s: s.lower())

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP_DTWT(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Depth to Water Table, dominant component
    #
    # Aggregate mapunit-component data to the map unit level using dominant component
    # and the tie breaker setting to select the lowest or highest monthly rating.
    # Use this for COMONTH table. domainValues
    #
    # PROBLEMS with picking the correct depth for each component. Use tiebreaker to pick
    # highest or lowest month and then aggregate to DCP?
    # Added areasymbol to output

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()

        inFlds = ["MUKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dAreasym = dict()
        dataCnt = int(arcpy.GetCount_management(initialTbl).getOutput(0))

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
            #cnt = 0
            #PrintMsg(" \nReading input table " + os.path.basename(initialTbl) + "...", 1)
            arcpy.SetProgressor("step", "Reading input table " + os.path.basename(initialTbl) + "...", 0, dataCnt, 1 )

            # "MUKEY", "COMPPCT_R", attribcolumn
            for rec in cur:
                arcpy.SetProgressorPosition()

                #arcpy.SetProgressorLabel("Reading input record (" + Number_Format(cnt, 0, True) + ")")
                mukey, compPct, rating, areasym = rec
                #mukey = rec[0]
                #compPct = rec[1]
                #rating = rec[2]
                dAreasym[mukey] = areasym

                #if rating is None:
                #    rating = nullRating

                try:
                    dMapunit[mukey].append([compPct, rating])

                except:
                    dMapunit[mukey] = [[compPct, rating]]


        del initialTbl  # Trying to save some memory 2016-06-23


        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            #PrintMsg(" \nWriting to output table " + outputTbl + "...", 1)
            arcpy.SetProgressor("step", "Writing to output table (" + os.path.basename(outputTbl) + ")", 0, len(dMapunit), 1 )

            for mukey, coVals in dMapunit.items():
                arcpy.SetProgressorPosition()
                # Grab the first pair of values (pct, depth) from the sorted list.
                # This is the dominant component rating using tie breaker setting
                #dcpRating = SortData(coVals, 0, 1, True, True)
                dcpRating = SortData(coVals, 0, 1, True, False)  # For depth to water table, we want the lower value (closer to surface)

                if bVerbose and mukey == '459272':
                    PrintMsg("\tDCP Rating for " + mukey + ": " + str(dcpRating) + " and rest: " + str(coVals), 1)

                rec =[mukey, dcpRating[0], dcpRating[1], dAreasym[mukey]]
                ocur.insertRow(rec)

                if not rec[2] in outputValues and not rec[2] is None:
                    outputValues.append(rec[2])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCD_DTWT(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition
    # and the tie breaker setting to select the lowest or highest monthly rating.
    # Use this for COMONTH table. domainValues
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # MUKEY,COKEY , COMPPCT_R, attribcolumn
            for rec in cur:
                mukey, cokey, compPct, rating, areasym = rec

                if rating is None:
                    rating = nullRating

                dAreasym[mukey] = areasym

                # Save list of cokeys for each mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            for cokey, coVals in dComponent.items():
                # Find high or low value for each component
                dCoRating[cokey] = max(coVals[1])

        else:
            for cokey, coVals in dComponent.items():
                # Find high or low value for each component
                dCoRating[cokey] = min(coVals[1])


        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                rating = dCoRating[cokey]
                compPct = dComponent[cokey][0]

                try:
                    dMuRatings[rating] += compPct

                except:
                    dMuRatings[rating] = compPct

            for rating, compPct in dMuRatings.items():
                # Find rating with highest sum of comppct
                if compPct > domPct:
                    domPct = compPct
                    dFinalRatings[mukey] = [compPct, rating]
                    #PrintMsg("\t" + mukey + ", " + str(compPct) + "%" + ", " + str(rating) + "cm", 1)

            del dMuRatings

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey, vals in dFinalRatings.items():
                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not rec[2] in outputValues and not rec[2] is None:
                    outputValues.append(rec[2])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_MaxMin(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Aggregate mapunit-component data to the map unit level using Minimum or Maximum
    # based upon the TieBreak rule.
    # Use this for COMONTH table. Example Depth to Water Table.
    #
    # It appears that WSS includes 0 percent components in the MinMax. This function
    # is currently set to duplicate this behavior
    # Added areasymbol to output
    #
    # Seems to be a problem with TitleCase Values in maplegendxml vs. SentenceCase in the original data. Domain values are SentenceCase.
    #

    try:
        #
        #bVerbose = True

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try later to substitute dSDV["nullratingreplacementvalue"]
        #whereClause = "COMPPCT_R >=  " + str(cutOff) + " and not " + dSDV["attributecolumnname"].upper() + " is null"
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # MUKEY,COKEY , COMPPCT_R, attribcolumn
            for rec in cur:

                mukey, cokey, compPct, rating, areasym = rec
                dAreasym[mukey] = areasym
                #PrintMsg("\t" + str(rec), 1)


                # Save list of cokeys for each mapunit-mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # This is working correctly for DTWT
            # Backwards for Ponding

            # Identify highest value for each component
            for cokey, coVals in dComponent.items():
                # Find high value for each component
                #PrintMsg("Higher values for " + cokey + ": " + str(coVals) + " = " + str(max(coVals[1])), 1)
                dCoRating[cokey] = max(coVals[1])

        else:
            # This is working correctly for DTWT
            # Backwards for Ponding

            # Identify lowest value for each component
            for cokey, coVals in dComponent.items():
                # Find low rating value for each component
                #PrintMsg("Lower values for " + cokey + ": " + str(coVals) + " = " + str(min(coVals[1])), 1)
                dCoRating[cokey] = min(coVals[1])


        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                try:
                    rating = dCoRating[cokey]
                    compPct = dComponent[cokey][0]

                    try:
                        dMuRatings[rating] += compPct

                    except:
                        dMuRatings[rating] = compPct

                except:
                    pass

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # This is working correctly for DTWT
                # Backwards for Ponding
                highRating = 0

                for rating, compPct in dMuRatings.items():
                    # Find the highest
                    if rating > highRating:
                        highRating = rating
                        dFinalRatings[mukey] = [compPct, rating]
            else:
                # This is working correctly for DTWT
                # Backwards for Ponding
                lowRating = nullRating

                for rating, compPct in dMuRatings.items():

                    if rating < lowRating and rating is not None:
                        lowRating = rating
                        dFinalRatings[mukey] = [compPct, rating]

            del dMuRatings

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dMapunit):

                try:
                    vals = dFinalRatings[mukey]

                except:
                    sumPct = 0
                    for cokey in dMapunit[mukey]:
                        try:
                            sumPct += dComponent[cokey][0]

                        except:
                            pass

                    vals = [sumPct, nullRating]

                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not rec[2] in outputValues and not rec[2] is None:
                    outputValues.append(rec[2])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_Mo_DCD(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Aggregate mapunit-component data to the map unit level using the dominant condition
    # based upon the TieBreak rule.
    # Use this for COMONTH table. Example Depth to Water Table.
    #
    # It appears that WSS includes 0 percent components in the MinMax. This function
    # is currently set to duplicate this behavior
    #
    # Currently there is a problem with the comppct. It ends up being 12X.

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try to substitute dSDV["nullratingreplacementvalue"]
        #whereClause = "COMPPCT_R >=  " + str(cutOff) + " and not " + dSDV["attributecolumnname"].upper() + " is null"
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # MUKEY,COKEY , COMPPCT_R, attribcolumn
            for rec in cur:
                #mukey = rec[0]; cokey = rec[1]; compPct = rec[2]; rating = rec[3]
                mukey, cokey, compPct, rating, areasym = rec
                if rating is None:
                    rating = 201

                # Save list of cokeys for each mapunit-mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]
                    dAreasymbols[mukey] = areasym

                try:
                    # if the rating value meets the tiebreak rule, save the rating value along with comppct for each component
                    #if not rating is None:
                    if tieBreaker == dSDV["tiebreakhighlabel"]:
                        if rating > dComponent[cokey][1]:
                            dComponent[cokey][1] = rating

                    elif rating < dComponent[cokey][1]:
                        dComponent[cokey][1] = rating

                except:
                    #  Save rating value along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, rating]

        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()
            dMuRatings[mukey] = [None, None]  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                if cokey in dComponent:

                    compPct, rating = dComponent[cokey]

                    if compPct > domPct:
                        domPct = compPct
                        dMuRatings[mukey] = [compPct, rating]
                        PrintMsg("\t" + mukey + ":" + cokey  + ", " + str(compPct) + "%, " + rating, 1)

            dFinalRatings[mukey] = dMuRatings[mukey]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dFinalRatings):
                compPct, rating = dFinalRatings[mukey]
                rec = mukey, compPct, rating, dAreasymbols[mukey]
                ocur.insertRow(rec)

                if not rating in outputValues and not rating is None:
                    outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_DCP_Domain(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Use this function for Flooding or Ponding Frequency which involves the COMONTH table
    #
    # Need to modify this so that COMPPCT_R is summed using just one value per component, not 12X.
    #
    # We have a case problem with Flooding Frequency Class: 'Very frequent'

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dCase = dict()
        dAreasym = dict()

        # Read initial table for non-numeric data types
        # 02-03-2016 Try adding 'choice' to this method to see if it handles Cons. Tree/Shrub better
        # than the next method. Nope, did not work. Still have case problems.
        #
        if dSDV["attributelogicaldatatype"].lower() == "string":
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"].lower() + "-type values : " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead.
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                        dCompPct[rec[1]] = rec[2]
                        dCase[str(rec[3]).upper()] = rec[3]  # save original value using uppercase key


                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        elif dSDV["attributelogicaldatatype"].lower() in ["float", "integer", "choice"]:
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        #PrintMsg(" \ndomainValues is empty, but legendValues has " + str(legendValues), 1)
                        dCase[str(rec[3]).upper()] = rec[3]

                        if str(rec[3]).upper() in dValues:
                            dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                            dCompPct[rec[1]] = rec[2]

                            # compare actual rating value to domainValues to make sure case is correct
                            if not rec[3] in domainValues: # this is a case problem
                                # replace the original dValue item
                                dValues[str(rec[3]).upper()][1] = rec[3]
                                # replace the value in domainValues list
                                for i in range(len(domainValues)):
                                    if domainValues[i].upper() == rec[3].upper():
                                        domainValues[i] = rec[3]

                        else:
                            # dValues is keyed on uppercase string rating
                            #
                            if not str(rec[3]) in missingDomain:
                                # Try to add missing value to dDomainValues dict and domainValues list
                                dValues[str(rec[3]).upper()] = [len(dValues), rec[3]]
                                domainValues.append(rec[3])
                                domainValuesUp.append(rec[3].upper())
                                missingDomain.append(str(rec[3]))
                                #PrintMsg("\tAdding value '" + str(rec[3]) + "' to domainValues", 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        else:
            PrintMsg(" \nProblem with handling domain values of type '" + dSDV["attributelogicaldatatype"] + "'", 1)

        # Aggregate monthly index values to a single value for each component
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        PrintMsg(" \nNot sure about this sorting code for tiebreaker", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # "Higher" (default for flooding and ponding frequency)
            for cokey, indexes in dComp.items():
                val = sorted(indexes, reverse=True)[0]
                dComp[cokey] = val
        else:
            for cokey, indexes in dComp.items():
                val = sorted(indexes)[0]
                dComp[cokey] = val

        # Save list of component data to each mapunit
        dRatings = dict()

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # Default for flooding and ponding frequency
                #
                #PrintMsg(" \ndomainValues: " + str(domainValues), 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        #PrintMsg("\tB ratingIndx: " + str(dComp[cokey]), 1)
                        compPct = dCompPct[cokey]
                        ratingIndx = dComp[cokey]

                        if ratingIndx in dRating:
                            sumPct = dRating[ratingIndx] + compPct
                            dRating[ratingIndx] = sumPct  # this part could be compacted

                        else:
                            dRating[ratingIndx] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], x[1]))[0]  # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=True)[0]
                    muVal = SortData(muVals, 0, 1, True, True)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

            else:
                # Lower
                PrintMsg(" \nFinal lower tiebreaker", 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], -x[1]))[0] # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=False)[0]
                    muVal = SortData(muVals, 0, 1, True, False)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])


        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues



## ===================================================================================
def AggregateCo_Mo_DCD_Domain(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Flooding or ponding frequency, dominant condition
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition.
    # Use domain values to determine sort order for tiebreaker
    #
    # Need to modify this function to correctly sum the comppct_r for the final output table.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        #bVerbose = False

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        if bNulls:
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        else:
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dAreasym = dict()
        dCase = dict()

        # Read initial table for non-numeric data types. Capture domain values and all component ratings.
        #


        if not dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:  # Changed here 2016-04-28
            #
            # No domain values for non-interp string ratings
            # !!! Probably never using this section of code.
            #
            if bVerbose:
                PrintMsg(" \n???dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg("domainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                if bVerbose:
                    PrintMsg(" \nReading initial data...", 1)

                for rec in cur:
                    # "MUKEY", "COKEY", "COMPPCT_R", RATING
                    mukey, cokey, compPct, rating, areasym = rec
                    dAreasym[mukey] = areasym
                    dComp[cokey] = rating
                    dCompPct[cokey] = compPct
                    dCase[str(rating).upper()] = rating  # save original value using uppercase key

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        elif dSDV["attributelogicaldatatype"].lower() in ["string", "float", "integer", "choice"]:
            # Flooding and Ponding would fall in this section

            if bVerbose:
                PrintMsg(" \ndValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues) + " \n ", 1)

            if len(domainValues) > 1 and not "None" in domainValues:
                dValues["NONE"] = [len(dValues), None]
                domainValues.append("None")

            if  dSDV["tiebreakdomainname"] is None:
                # There are no domain values. We must make sure that the legend values are the same as
                # the output values.
                #
                #PrintMsg(" \nNo domain name for this property", 1)

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    if bVerbose:
                        PrintMsg(" \nReading initial data...", 1)

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "MUKEY", "COKEY", "COMPPCT_R", RATING
                        #PrintMsg("\t" + str(rec), 1)
                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating

                            if str(rating).upper() in dValues:
                                #PrintMsg("\tNew rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                #dComp[cokey] = rating
                                dValues[str(rating).upper()][1] = rating
                                dCompPct[cokey] = compPct

                                # compare actual rating value to domainValues to make sure case is correct
                                #
                                # This does not make sense. domainValues must be coming from maplegendxml.
                                #
                                if not rating in domainValues: # this is a case problem
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct

                                    #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)


            else:
                # New code
                #PrintMsg(" \nDomain name for this property: '" + dSDV["tiebreakdomainname"] + "'", 1)

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    if bVerbose:
                        PrintMsg(" \nReading initial data...", 1)

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "MUKEY", "COKEY", "COMPPCT_R", RATING
                        #PrintMsg("\t" + str(rec), 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating

                            if str(rating).upper() in dValues:
                                #PrintMsg("\tNew rating '" + rating + "' assigning index'" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                dCompPct[cokey] = compPct

                                # compare actual rating value to domainValues to make sure case is correct
                                if not rating in domainValues: # this is a case problem
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct

                                    #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)



        else:
            raise MyError, "Problem with handling domain values of type '" + dSDV["attributelogicaldatatype"]

        # Aggregate monthly index values to a single value for each component??? Would it not be better to
        # create a new function for COMONTH-DCD? Then I could simplify this function.
        #
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        #if not dSDV["attributelogicaldatatype"].lower() in ["string", "vText"]:

        if bVerbose:
            PrintMsg(" \nAggregating to a single value per component which would generally only apply to COMONTH properties?", 1)


        # Save list of component rating data to each mapunit, sort and write out
        # a single map unit rating
        #
        dRatings = dict()

        if bVerbose:
            PrintMsg(" \nWriting map unit rating data to final output table", 1)
            PrintMsg(" \nUsing tiebreaker '" + tieBreaker + "' (where choices are " + dSDV["tiebreaklowlabel"] + " or " + dSDV["tiebreakhighlabel"] + ")", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for mukey, cokeys in dMapunit.items():
                    # Since this is COMONTH data, each cokey could be listed 12X.
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + " cokeys: " + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #This is the final aggregation from component to map unit rating
                    muVal = SortData(muVals, 0, 1, True, True)
                    comppct = muVal[0] / 12
                    newrec = [mukey, comppct, domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

        else:
            # tieBreaker Lower
            # Overhauling this tiebreaker lower, need to do the rest once it is working properly
            #
            #PrintMsg(" \nActually in Lower tiebreaker code", 1)
            #PrintMsg("dMapunit has " + str(len(dMapunit)) + " records", 1 )

            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                # Process all mapunits
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + ":" + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            comppct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            #PrintMsg("\t" + cokey + " index: " + str(ratingIndx), 1)

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + comppct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = comppct

                        except:
                            errorMsg()

                    for ratingIndx, comppct in dRating.items():
                        muVals.append([comppct, ratingIndx])  # This muVal is not being populated

                    #PrintMsg("\t" + str(dRating), 1)

                    if len(muVals) > 0:
                        muVal = SortData(muVals, 0, 1, True, False)
                        PrintMsg("\tMukey: " + mukey + ", " + str(muVal), 1)
                        comppct = muVal[0] / 12
                        ratingIndx = muVal[1]
                        #compPct, ratingIndx = muVal
                        rating = domainValues[ratingIndx]

                    else:
                        rating = None
                        comppct = None

                    #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                    #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                    newrec = [mukey, comppct, rating, dAreasym[mukey]]

                    ocur.insertRow(newrec)

                    if not rating in outputValues and not rating is None:
                        outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_WTA(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Aggregate monthly depth to water table to the map unit level using a special type
    # of Weighted average.
    #
    # Web Soil Survey takes only the Lowest or Highest of the monthly values from
    # each component and calculates the weighted average of those.
    #

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try to substitute dSDV["nullratingreplacementvalue"]
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # MUKEY,COKEY , COMPPCT_R, attribcolumn
            for rec in cur:

                mukey, cokey, compPct, rating, areasym = rec
                dAreasym[mukey] = areasym

                # Save list of cokeys for each mapunit
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # This is working correctly for DepthToWaterTable

            # Identify highest value for each component
            for cokey, coVals in dComponent.items():
                # Find highest monthly value for each component
                #PrintMsg("Higher values for cokey " + cokey + ": " + str(coVals[1]) + " = " + str(max(coVals[1])), 1)
                dCoRating[cokey] = max(coVals[1])

        else:
            # This is working correctly for DepthToWaterTable

            # Identify lowest monthly value for each component
            for cokey, coVals in dComponent.items():
                # Find low rating value for each component
                #PrintMsg("Lower values for cokey " + cokey + ": " + str(coVals[1]) + " = " + str(min(coVals[1])), 1)
                dCoRating[cokey] = min(coVals[1])


        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            #dMuRatings = dict()  # create a dictionary of values for just this map unit
            muPct = 0
            muRating = None

            for cokey in cokeys:
                # look at values for each component within the map unit
                try:
                    rating = dCoRating[cokey]
                    compPct = dComponent[cokey][0]
                    muPct += compPct

                    if not rating is None:
                      # accumulate product of depth and component percent
                      try:
                          muRating += (compPct * rating)

                      except:
                          muRating = compPct * rating

                except:
                    pass

            # Calculate weighted mapunit value from sum of products
            if not muRating is None:
                muRating = muRating / float(muPct)

            dFinalRatings[mukey] = [muPct, muRating]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dMapunit):
                compPct, rating = dFinalRatings[mukey]
                rec = mukey, compPct, rating, dAreasym[mukey]
                ocur.insertRow(rec)

                if not rating in outputValues and not rating is None:
                    outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_WTA_DTWT(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # In the process of converting DCD to WTA

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # MUKEY,COKEY , COMPPCT_R, attribcolumn
            for rec in cur:
                #mukey = rec[0]
                #cokey = rec[1]
                #compPct = rec[2]
                #rating = rec[3]
                mukey, cokey, compPct, rating, areasym = rec

                dAreasym[mukey] = areasym

                if rating is None:
                    rating = nullRating

                # Save list of cokeys for each mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    dComponent[cokey] = [compPct, [rating]]


        if tieBreaker == dSDV["tiebreakhighlabel"]:
            for cokey, coVals in dComponent.items():
                # Find high value for each component
                dCoRating[cokey] = max(coVals[1])

        else:
            for cokey, coVals in dComponent.items():
                # Find low value for each component
                dCoRating[cokey] = min(coVals[1])

        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            sumPct = 0
            muProd = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                rating = dCoRating[cokey]
                compPct = dComponent[cokey][0]

                #if rating != nullRating:
                if not rating is None:
                    # Don't include the 201 (originally null) depths in the WTA calculation
                    sumPct += compPct            # sum comppct for the mapunit
                    muProd += (rating * compPct)   # calculate product of component percent and component rating

            if sumPct > 0:
                dFinalRatings[mukey] = [sumPct, round(float(muProd) / sumPct)]

            else:
                # now replace the nulls with 201
                dFinalRatings[mukey] = [100, nullRating]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey, vals in dFinalRatings.items():
                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not vals[1] in outputValues and not vals[1] is None:
                    outputValues.append(vals[1])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_DCD_Domain(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Flooding or ponding frequency, dominant condition
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition.
    # Use domain values to determine sort order for tiebreaker
    #
    # Problem with domain values for some indexes which are numeric. Need to accomodate for
    # domain key values which cannot be 'uppercased'.
    #
    # Some domain values are not found in the data and vise versa.
    #
    # Bad problem 2016-06-08.
    # Noticed that my final rating table may contain multiple ratings (tiebreak) for a map unit. This creates
    # a funky join that may display a different map color than the Identify value shows for the polygon. NIRRCAPCLASS.
    # Added areasymbol to output
    #
    # Conservation Tree and Shrub group are located in the component table
    # This has domain values and component values which are all lowercase
    # The maplegendxml is all uppercase
    #
    # I think I need to loop through each output value from the table, find the UPPER match and
    # then alter the legend value and label to match the output value.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        if bNulls:
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        else:
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dAreasym = dict()
        dCase = dict()

        # Read initial table for non-numeric data types. Capture domain values and all component ratings.
        #
        if bVerbose:
            PrintMsg(" \nReading initial data...", 1)

        if not dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:  # Changed here 2016-04-28
            # No domain values for non-interp string ratings
            # Probably not using this section of code.
            #
            if bVerbose:
                PrintMsg(" \n???dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg("domainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    # "MUKEY", "COKEY", "COMPPCT_R", RATING
                    mukey, cokey, compPct, rating, areasym = rec
                    dAreasym[mukey] = areasym

                    #try:
                        #PrintMsg("\t" + str(rec), 1)
                        # capture component ratings as index numbers instead.
                        #dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])
                    #    dComp[cokey].append(rating)
                    #    dCompPct[cokey] = compPct

                    #except:
                    #dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]  #error
                    dComp[cokey] = rating
                    dCompPct[cokey] = compPct
                    dCase[str(rating).upper()] = rating  # save original value using uppercase key

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        elif dSDV["attributelogicaldatatype"].lower() in ["string", "float", "integer", "choice"]:
            #
            # if dSDV["tiebreakdomainname"] is not None:  # this is a test to see if there are true domain values
            # Use this to compare dValues to output values
            #


            if bVerbose:
                PrintMsg(" \ndValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues) + " \n ", 1)

            if len(domainValues) > 1 and not "NONE" in domainValues:
                dValues["NONE"] = [len(dValues), None]
                domainValues.append("NONE")

            if  dSDV["tiebreakdomainname"] is None:
                # There are no domain values. We must make sure that the legend values are the same as
                # the output values.
                #
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "MUKEY", "COKEY", "COMPPCT_R", RATING
                        #PrintMsg("\t" + str(rec), 1)
                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating

                            if str(rating).upper() in dValues:
                                #PrintMsg("\tNew rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                #dComp[cokey] = rating
                                dValues[str(rating).upper()][1] = rating
                                dCompPct[cokey] = compPct

                                # compare actual rating value to domainValues to make sure case is correct
                                #
                                # This does not make sense. domainValues must be coming from maplegendxml.
                                #
                                if not rating in domainValues: # this is a case problem
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct

                                    #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)

            else:
                # New code

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "MUKEY", "COKEY", "COMPPCT_R", RATING
                        #PrintMsg("\t" + str(rec), 1)


                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating

                            if str(rating).upper() in dValues:
                                #PrintMsg("\tNew rating '" + rating + "' assigning index'" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                dCompPct[cokey] = compPct

                                # compare actual rating value to domainValues to make sure case is correct
                                if not rating in domainValues: # this is a case problem
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct

                                    #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)



        else:
            raise MyError, "Problem with handling domain values of type '" + dSDV["attributelogicaldatatype"]

        # Aggregate monthly index values to a single value for each component??? Would it not be better to
        # create a new function for COMONTH-DCD? Then I could simplify this function.
        #
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        #if not dSDV["attributelogicaldatatype"].lower() in ["string", "vText"]:

        if bVerbose:
            PrintMsg(" \nAggregating to a single value per component which would generally only apply to COMONTH properties?", 1)


        if 1 == 2:
            if not dSDV["attributelogicaldatatype"].lower() in ["vText"]:

                if tieBreaker == dSDV["tiebreaklowlabel"]:
                    # Lower

                    if bVerbose:
                        PrintMsg(" \nAggregating to a single " +  tieBreaker + " value per component", 1)

                    for cokey, indexes in dComp.items():

                        if len(indexes) > 1:
                            val = sorted(indexes, reverse=True)[0]

                        else:
                            val = indexes[0]

                        #PrintMsg("\tval: " + str(indexes), 1)
                        dComp[cokey] = val

                else:
                    # Higher
                    if bVerbose:
                        PrintMsg(" \nAggregating to a single " +  tieBreaker + " value per component", 1)

                    for cokey, indexes in dComp.items():
                        if len(indexes) > 1: # inefficient vay of handling Nulls. Need to improve this.
                            val = sorted(indexes, reverse=False)[0]

                        else:
                            val = indexes[0]

                        dComp[cokey] = val


            else:
                # VTEXT data which would also include interps
                #
                #PrintMsg(" \nProblem here", 1)
                for cokey, indexes in dComp.items():
                    #PrintMsg("\tIndexes = " + str(indexes), 1)
                    dComp[cokey] = indexes
                    #val = sorted(indexes)[0]
                    #dComp[cokey] = val



        # Save list of component rating data to each mapunit, sort and write out
        # a single map unit rating
        #
        dRatings = dict()

        if bVerbose:
            PrintMsg(" \nWriting map unit rating data to final output table", 1)
            PrintMsg(" \nUsing tiebreaker '" + tieBreaker + "' (where choices are " + dSDV["tiebreaklowlabel"] + " or " + dSDV["tiebreakhighlabel"] + ")", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #This is the final aggregation from component to map unit rating
                    muVal = SortData(muVals, 0, 1, True, True)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

        else:
            # tieBreaker Lower
            # Overhauling this tiebreaker lower, need to do the rest once it is working properly
            #
            #PrintMsg(" \nActually in Lower tiebreaker code", 1)
            #PrintMsg("dMapunit has " + str(len(dMapunit)) + " records", 1 )

            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                # Process all mapunits
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + ":" + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            #PrintMsg("\t" + cokey + " index: " + str(ratingIndx), 1)

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            errorMsg()

                    for ratingIndx, compPct in dRating.items():
                        muVals.append([compPct, ratingIndx])  # This muVal is not being populated

                    #PrintMsg("\t" + str(dRating), 1)

                    if len(muVals) > 0:
                        muVal = SortData(muVals, 0, 1, True, False)
                        #PrintMsg("\tMukey: " + mukey + ", " + str(muVal), 1)
                        compPct, ratingIndx = muVal
                        rating = domainValues[ratingIndx]

                    else:
                        rating = None
                        compPct = None

                    #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                    #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                    newrec = [mukey, compPct, rating, dAreasym[mukey]]

                    ocur.insertRow(newrec)

                    if not rating in outputValues and not rating is None:
                        outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP_Domain(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # I may not use this function. Trying to handle ratings with domain values using the
    # standard AggregateCo_DCP function
    #
    # Flooding or ponding frequency, dominant component with domain values
    #
    # Use domain values to determine sort order for tiebreaker
    #
    # Problem with domain values for some indexes which are numeric. Need to accomodate for
    # domain key values which cannot be 'uppercased'.
    # Added areasymbol to output

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dCase = dict()
        dAreasym = dict()

        # Read initial table for non-numeric data types
        # 02-03-2016 Try adding 'choice' to this method to see if it handles Cons. Tree/Shrub better
        # than the next method. Nope, did not work. Still have case problems.
        #
        if dSDV["attributelogicaldatatype"].lower() == "string":
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"].lower() + "-type values : " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead.
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                        dCompPct[rec[1]] = rec[2]
                        dCase[str(rec[3]).upper()] = rec[3]  # save original value using uppercase key


                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        elif dSDV["attributelogicaldatatype"].lower() in ["float", "integer", "choice"]:
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        #PrintMsg(" \ndomainValues is empty, but legendValues has " + str(legendValues), 1)
                        dCase[str(rec[3]).upper()] = rec[3]

                        if str(rec[3]).upper() in dValues:
                            dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                            dCompPct[rec[1]] = rec[2]

                            # compare actual rating value to domainValues to make sure case is correct
                            if not rec[3] in domainValues: # this is a case problem
                                # replace the original dValue item
                                dValues[str(rec[3]).upper()][1] = rec[3]
                                # replace the value in domainValues list
                                for i in range(len(domainValues)):
                                    if domainValues[i].upper() == rec[3].upper():
                                        domainValues[i] = rec[3]

                        else:
                            # dValues is keyed on uppercase string rating
                            #
                            if not str(rec[3]) in missingDomain:
                                # Try to add missing value to dDomainValues dict and domainValues list
                                dValues[str(rec[3]).upper()] = [len(dValues), rec[3]]
                                domainValues.append(rec[3])
                                domainValuesUp.append(rec[3].upper())
                                missingDomain.append(str(rec[3]))
                                #PrintMsg("\tAdding value '" + str(rec[3]) + "' to domainValues", 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        else:
            PrintMsg(" \nProblem with handling domain values of type '" + dSDV["attributelogicaldatatype"] + "'", 1)

        # Aggregate monthly index values to a single value for each component
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        PrintMsg(" \nNot sure about this sorting code for tiebreaker", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # "Higher" (default for flooding and ponding frequency)
            for cokey, indexes in dComp.items():
                val = sorted(indexes, reverse=True)[0]
                dComp[cokey] = val
        else:
            for cokey, indexes in dComp.items():
                val = sorted(indexes)[0]
                dComp[cokey] = val

        # Save list of component data to each mapunit
        dRatings = dict()

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # Default for flooding and ponding frequency
                #
                #PrintMsg(" \ndomainValues: " + str(domainValues), 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        #PrintMsg("\tB ratingIndx: " + str(dComp[cokey]), 1)
                        compPct = dCompPct[cokey]
                        ratingIndx = dComp[cokey]

                        if ratingIndx in dRating:
                            sumPct = dRating[ratingIndx] + compPct
                            dRating[ratingIndx] = sumPct  # this part could be compacted

                        else:
                            dRating[ratingIndx] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], x[1]))[0]  # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=True)[0]
                    muVal = SortData(muVals, 0, 1, True, True)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])

            else:
                # Lower
                PrintMsg(" \nFinal lower tiebreaker", 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], -x[1]))[0] # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=False)[0]
                    muVal = SortData(muVals, 0, 1, True, False)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] in outputValues and not newrec[2] is None:
                        outputValues.append(newrec[2])


        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_WTA(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component data to the map unit level using a weighted average
    #
    try:
        #bVerbose = True

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"].upper() + " DESC")

        if bZero == False:
            # ignore any null values
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        #prec = dSDV["attributeprecision"]
        outputValues = [999999999, -9999999999]
        recCnt = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    recCnt += 1
                    mukey, cokey, comppct, val, areasym = rec

                    if val is None and bZero:
                        # convert null values to zero
                        val = 0

                    if mukey != lastMukey and lastMukey != "xxxx":
                        if sumPct > 0 and sumProd is not None:
                            # write out record for previous mapunit

                            meanVal = round(float(sumProd) / sumPct, fldPrecision)
                            newrec = [lastMukey, sumPct, meanVal, areasym]
                            ocur.insertRow(newrec)

                            # save max-min values
                            if not meanVal is None:
                                outputValues[0] = min(meanVal, outputValues[0])

                            outputValues[1] = max(meanVal, outputValues[1])

                        # reset variables for the next mapunit record
                        sumPct = 0
                        sumProd = None

                    # set new mapunit flag
                    lastMukey = mukey

                    # accumulate data for this mapunit
                    sumPct += comppct

                    if val is not None:
                        prod = comppct * val
                        try:
                            sumProd += prod

                        except:
                            sumProd = prod

                # Add final record
                newrec = [lastMukey, sumPct, meanVal, areasym]
                ocur.insertRow(newrec)

        outputValues.sort()

        if outputValues[0] == 999999999.0 or outputValues[1] == -999999999.0:
            # Sometimes no data can skip through the max min test
            outputValues = [0.0, 0.0]
            raise MyError, "No data for " + sdvAtt

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def Aggregate2_NCCPI(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component data to the map unit level using a weighted average
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, " + dSDV["attributecolumnname"] + " DESC")

        # Need to check WSS to see if 'Treat nulls as zero' affects NCCPI
        #
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = None
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    mukey, cokey, comppct, val, areasym = rec
                    #PrintMsg(mukey + ", " + str(comppct) + ", " + str(val), 1)

                    if mukey != lastMukey and lastMukey != "xxxx":
                        if sumPct > 0 and sumProd is not None:
                            # write out record for previous mapunit
                            meanVal = round(float(sumProd) / sumPct, fldPrecision)
                            newrec = [lastMukey, sumPct, meanVal, areasym]
                            ocur.insertRow(newrec)

                        # reset variables for the next mapunit record
                        sumPct = 0
                        sumProd = None


                    # set new mapunit flag
                    lastMukey = mukey

                    # accumulate data for this mapunit
                    sumPct += int(comppct)

                    if val is not None:
                        #prod = int(comppct) * float(val)  # why the int()??
                        prod = float(comppct) * float(val)

                        try:
                            sumProd += prod

                        except:
                            sumProd = prod

                # Add final record
                newrec = [lastMukey, sumPct, meanVal, areasym]
                ocur.insertRow(newrec)
                #PrintMsg(" \nLast record: " + str(newrec), 0)


        #outputValues.sort()
        #PrintMsg(" \nNCCPI outputValues: " + str(outputValues), 1)
        outputValues = [0.0, 1.0]
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_PP_SUM(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Aggregate data to the map unit level using a sum (Hydric)
    # This is Percent Present
    # Soil Data Viewer reports zero for non-Hydric map units. This function is
    # currently not creating a record for those because they are not included in the
    # sdv_initial table.
    #
    # Will try removing sql whereclause from cursor and apply it to each record instead.
    #
    # Added Areasymbol to output

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["MUKEY", "AREASYMBOL", "COMPPCT_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]  # not sure why I have AREASYMBOL on the end..
        outFlds = ["MUKEY", "AREASYMBOL", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        inFlds = ["MUKEY", "AREASYMBOL", "COMPPCT_R", dSDV["attributecolumnname"].upper()]  # not sure why I have AREASYMBOL on the end..
        outFlds = ["MUKEY", "AREASYMBOL", dSDV["resultcolumnname"].upper()]

        sqlClause =  (None, "ORDER BY MUKEY ASC")

        # For Percent Present, do not apply the whereclause to the cursor. Wait
        # and use it against each record so that all map units are rated.
        #whereClause = dSDV["sqlwhereclause"]
        whereClause = ""
        hydric = dSDV["sqlwhereclause"].split("=")[1].encode('ascii').strip().replace("'","")
        #PrintMsg(" \n" + attribcolumn + " = " + hydric, 1)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        # Create outputTbl based upon initialTbl schema
        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        iMax = -9999999999
        iMin = 9999999999

        if bVerbose:
            PrintMsg(" \nReading " + initialTbl + " and writing to " + outputTbl, 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    mukey, areasym, comppct, val= rec

                    if comppct is None:
                        comppct = 0

                    if mukey != lastMukey and lastMukey != "xxxx":
                        #if sumPct > 0:
                        # write out record for previous mapunit
                        newrec = [lastMukey, areasym, sumPct]
                        ocur.insertRow(newrec)
                        iMax = max(sumPct, iMax)

                        if not sumPct is None:
                            iMin = min(sumPct, iMin)

                        # reset variables for the next mapunit record
                        sumPct = 0

                    # set new mapunit flag
                    lastMukey = mukey

                    # accumulate data for this mapunit
                    if str(val).upper() == hydric.upper():
                        # using the sqlwhereclause on each record so that
                        # the 'NULL' hydric map units are assigned zero instead of NULL.
                        sumPct += comppct

                # Add final record
                newrec = [lastMukey, areasym, sumPct]
                ocur.insertRow(newrec)

        return outputTbl, [iMin, iMax]

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_WTA_SUM(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component-horizon data to the map unit level using a weighted average
    #
    # This version uses SUM for horizon data as in AWS
    # Added areasymbol to output
    #
    try:
        import decimal
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].upper()
        #resultcolumn = dSDV["resultcolumnname"].upper()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", "HZDEPT_R", "HZDEPB_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, HZDEPT_R ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        #prec = dSDV["attributeprecision"]
        roundOff = 2

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        if hzT > 0:
                            aws = float(hzT) * val
                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, aws, areasym]

                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dAWS, areasym = dComp[cokey]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dAWS, areasym]

                        #arcpy.SetProgressorPosition()

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, dRec in dComp.items():
                        # get component level data  CHK
                        mukey, comppct, hzT, val, areasym = dRec

                        # get sum of component percent for the mapunit  CHK
                        try:
                            sumCompPct = float(dPct[mukey])

                        except:
                            # set the component percent to zero if it is not found in the
                            # dictionary. This is probably a 'Miscellaneous area' not included in the  CHK
                            # data or it has no horizon information.
                            sumCompPct = 0

                        #PrintMsg(areasym + ", " + mukey + ", " + cokey + ", " + str(comppct) + ", " + str(sumCompPct) + ", " + str(hzT) + ", " + str(val), 1)  # These look good


                        # calculate component percentage adjustment

                        if sumCompPct > 0:
                            # If there is no data for any of the component horizons, could end up with 0 for
                            # sum of comppct_r
                            adjCompPct = float(comppct) / sumCompPct   # WSS method

                            # adjust the rating value down by the component percentage and by the sum of the
                            # usable horizon thickness for this component
                            aws = adjCompPct * val
                            hzT = hzT * adjCompPct    # Adjust component share of horizon thickness by comppct

                            # Update component values in component dictionary
                            dComp[cokey] = mukey, comppct, hzT, aws, areasym

                            # Populate dMu dictionary
                            if mukey in dMu:
                                val1, val3, areasym = dMu[mukey]
                                comppct = comppct + val1
                                aws = aws + val3

                            dMu[mukey] = [comppct, aws, areasym]

                # Write out map unit aggregated AWS
                #
                murec = list()
                outputValues= [999999999, -9999999999]

                for mukey, val in dMu.items():
                    compPct, aws, areasym = val
                    aws = round(aws, fldPrecision) # Test temporary removal of rounding
                    #aws = decimal.Decimal(str(aws)).quantize(decimal.Decimal("0.01"), decimal.ROUND_HALF_UP)
                    murec = [mukey, comppct, aws, areasym]
                    ocur.insertRow(murec)

                    # save max-min values
                    outputValues[0] = min(aws, outputValues[0])
                    outputValues[1] = max(aws, outputValues[1])

        outputValues.sort()

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_WTA_WTA(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component-horizon data to the map unit level using a weighted average
    #
    # This version uses weighted average for horizon data as in AWC and most others
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", "HZDEPT_R", "HZDEPB_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, HZDEPT_R ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon
                        #if hzdept == 0:
                        #    PrintMsg("\tFound horizon for mapunit (" + mukey + ":" + cokey + " with hzthickness of " + str(hzT), 1)

                        if hzT > 0:
                            aws = float(hzT) * val * comppct

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, aws, areasym]
                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dAWS, areasym = dComp[cokey]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dAWS, areasym]

                        #else:
                        #    PrintMsg("\tFound horizon for mapunit (" + mukey + ":" + cokey + " with hzthickness of " + str(hzT), 1)

                    #else:
                    #    PrintMsg("\tFound horizon with no data for mapunit (" + mukey + ":" + cokey + " with hzthickness of " + str(hzT), 1)

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)
                    #arcpy.SetProgressor("step", "Saving map unit and component AWS data...",  0, iComp, 1)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, hzT, cval, areasym = vals

                        # get sum of comppct for mapunit
                        sumPct = dPct[mukey]

                        # calculate component weighted values
                        # get weighted layer thickness
                        divisor = sumPct * hzT

                        if divisor > 0:
                            newval = float(cval) / divisor

                        else:
                            newval = 0.0

                        if mukey in dMu:
                            pct, mval, areasym = dMu[mukey]
                            newval = newval + mval

                        dMu[mukey] = [sumPct, newval, areasym]

                # Write out map unit aggregated AWS
                #
                murec = list()
                outputValues= [999999999, -9999999999]

                for mukey, vals in dMu.items():
                    sumPct, val, areasym = vals
                    aws = round(val, fldPrecision)
                    murec = [mukey, sumPct, aws, areasym]
                    ocur.insertRow(murec)
                    # save max-min values
                    outputValues[0] = min(aws, outputValues[0])
                    outputValues[1] = max(aws, outputValues[1])

        outputValues.sort()

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_DCP_WTA(gdb, sdvAtt, sdvFld, initialTbl):
    #
    # Dominant component for mapunit-component-horizon data to the map unit level
    #
    # This version uses weighted average for horizon data
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", "HZDEPT_R", "HZDEPB_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, HZDEPT_R ASC")
        #whereClause = "COMPPCT_R >=  " + str(cutOff)
        whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues= [999999999, -9999999999]

        if outputTbl == "":
            raise MyError,""

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        if hzT > 0:
                            #if bVerbose:
                            #    PrintMsg("\t" + mukey + "; " + cokey + ";  " + str(comppct) + "%;  " + str(max(hzdept, top)) + "; " + str(min(hzdepb, bot)) + "; " + str(hzT) + ", " + str(val), 1)

                            aws = float(hzT) * val

                            # Need to grab the top or dominant component for this mapunit
                            if not cokey in dComp and not mukey in dPct:
                                # Create initial entry for this component using the first horiozon CHK
                                #if bVerbose:
                                #    PrintMsg("\t" + mukey + "; " + cokey + ";  " + str(comppct) + "%;  " + str(max(hzdept, top)) + "c-->" + str(min(hzdepb, bot)) + "cm; "  + str(hzT) + "; " + str(val), 0)

                                dComp[cokey] = [mukey, comppct, hzT, aws, areasym]

                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                try:
                                    # For dominant component:
                                    # accumulate total thickness and total rating value by adding to existing component values  CHK
                                    mukey, comppct, dHzT, dAWS, areasym = dComp[cokey]
                                    dAWS = dAWS + aws
                                    dHzT = dHzT + hzT
                                    dComp[cokey] = [mukey, comppct, dHzT, dAWS, areasym]
                                    #PrintMsg("\t" + mukey + "; " + cokey + ";  " + str(comppct) + "%;  " + str(max(hzdept, top)) + "-->" + str(min(hzdepb, bot)) + "cm; " + str(hzT) + "; " + str(round(dAWS, 2)), 1)

                                except KeyError:
                                    # Hopefully this is a component other than dominant
                                    pass

                                except:
                                    errorMsg()

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    #arcpy.SetProgressor("step", "Saving map unit and component AWS data...",  0, iComp, 1)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, hzT, cval, areasym = vals

                        # get sum of comppct for mapunit
                        sumPct = dPct[mukey]

                        # calculate mean value for entire depth range
                        newval = float(cval) / hzT

                        if mukey in dMu:
                            pct, mval = dMu[mukey]
                            newval = newval + mval

                        dMu[mukey] = [sumPct, newval, areasym]

                # Write out map unit aggregated AWS
                #
                murec = list()
                for mukey, vals in dMu.items():
                    sumPct, val, areasym = vals
                    val = round(val, fldPrecision)
                    murec = [mukey, sumPct, val, areasym]
                    ocur.insertRow(murec)
                    #PrintMsg("\tMapunit: " + mukey + "; " + str(sumPct) + "%; " + str(val), 1)

                    # save max-min values
                    outputValues[0] = min(val, outputValues[0])
                    outputValues[1] = max(val, outputValues[1])

        outputValues.sort()

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateHz_MaxMin_WTA(gdb, sdvAtt, sdvFld, initialTbl):
    # Aggregate mapunit-component-horizon data to the map unit level using weighted average
    # for horizon data, but the assigns either the minimum or maximum component rating to
    # the map unit, depending upon the Tiebreaker setting.
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", "HZDEPT_R", "HZDEPB_R", dSDV["attributecolumnname"].upper(), "AREASYMBOL"]
        outFlds = ["MUKEY", "COMPPCT_R", dSDV["resultcolumnname"].upper(), "AREASYMBOL"]

        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, HZDEPT_R ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].upper() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        if hzT > 0:

                            rating = float(hzT) * val   # Not working for KFactor WTA
                            #rating = float(hzT) * float(val)   # Try floating the KFactor to see if that will work. Won't it still have to be rounded to standard KFactor index value?

                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, rating, areasym]

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dRating, areasym = dComp[cokey]
                                dRating += rating
                                dHzT += hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dRating, areasym]

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, hzT, cval, areasym = vals
                        rating = cval / hzT  # final horizon weighted average for this component
                        #PrintMsg("\t" + mukey + ", " + cokey + ", " + str(round(rating, 1)), 1)

                        try:
                            # append component weighted average rating to the mapunit dictionary
                            dMu[mukey].append([comppct, rating, areasym])

                        except:
                            # create a new mapunit record in the dictionary
                            dMu[mukey] = [[comppct, rating, areasym]]

                # Write out map unit aggregated rating
                #
                #murec = list()
                outputValues = [999999999, -9999999999]

                if tieBreaker == dSDV["tiebreakhighlabel"]:
                    for mukey, muVals in dMu.items():
                        muVal = SortData(muVals, 1, 0, True, True)
                        pct, val, areasym = muVal
                        rating = round(val, fldPrecision)
                        murec = [mukey, pct, rating, areasym]
                        ocur.insertRow(murec)
                        # save overall max-min values
                        outputValues[0] = min(rating, outputValues[0])
                        outputValues[1] = max(rating, outputValues[1])

                else:
                    # Lower
                    for mukey, muVals in dMu.items():
                        muVal = SortData(muVals, 1, 0, False, True)
                        pct, val, areasym = muVal
                        rating = round(val, fldPrecision)
                        murec = [mukey, pct, rating, areasym]
                        ocur.insertRow(murec)
                        # save overall max-min values
                        outputValues[0] = min(rating, outputValues[0])
                        outputValues[1] = max(rating, outputValues[1])

        if (bZero and outputValues ==  [0.0, 0.0]):
            PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def UpdateMetadata(outputWS, target, parameterString):
    #
    # Used for non-ISO metadata
    #
    # Search words:  xxSTATExx, xxSURVEYSxx, xxTODAYxx, xxFYxx
    #
    try:
        PrintMsg("\tUpdating metadata for the final rating table (" + os.path.basename(target) + ")...", 0)
        arcpy.SetProgressor("default", "Updating metadata")

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Define input and output XML files
        xmlPath = os.path.dirname(sys.argv[0])  # script directory
        mdExport = os.path.join(xmlPath, "SDV_Metadata.xml")        # original template metadata in script directory
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the temporary copy that will be edited

        # Cleanup output XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        # Convert XML to tree format
        tree = ET.parse(mdExport)
        root = tree.getroot()

        # List of items to be edited
        #  <identificationInfo><MD_DataIdentification><citation><CI_Citation><title><gco:CharacterString> SDV_Title
        #  <identificationInfo><MD_DataIdentification><abstract><gco:CharacterString> SDV_Description
        #  <identificationInfo><MD_DataIdentification><purpose><gco:CharacterString> SDV_Summary
        #  <identificationInfo><MD_DataIdentification><credit><gco:CharacterString>  SDV_Credits

        ns = "{http://www.isotc211.org/2005/gmd}"
        idInfo = ns + "identificationInfo"
        idElem = root.findall(idInfo)

        # Create dictionary containing output information
        # These are strings placed in the SDV_Metadata.xml file that will allow for search and replace.
        # To my disappointment, the Description metadata is not displayed in the ArcMap table description, only
        # in ArcCatalog metadata. Need to double-check to see if this is true in ArcGIS 10.3.
        #
        # PrintMsg(" \nAttributeDescription: \n " + dSDV["attributedescription"], 1)
        dMetadata = dict()
        dMetadata["SDV_Title"] = "Rating table for '" + dSDV["attributename"] + "' - " + aggMethod
        dMetadata["SDV_Description"] = "Map unit rating table for '" + dSDV["attributename"] +"'" + "\r" + dSDV["attributedescription"] + "\r" + parameterString
        dMetadata["SDV_Credits"] = "USDA-Natural Resources Conservation Service"
        dMetadata["SDV_Summary"] = "Map the '" + sdvAtt + "' soil " + dSDV["attributetype"].lower() + " by joining this rating table to the soil layer (polygon or raster) using the mukey field."
        abstract = ns + "abstract"

        for id in idElem:
            md = id.find(ns + "MD_DataIdentification")

            for s in md.iter():
                if s.tag.endswith("CharacterString"):
                    #PrintMsg("\t" + s.tag + ": " + s.text, 1)
                    if s.text in dMetadata:
                        s.text = dMetadata[s.text]

        #  create new xml file with edits
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        if not arcpy.Exists(mdImport):
            raise MyError, "Missing metadata template file (" + mdImport + ")"

        #else:
        #    PrintMsg("Found metadata template file (" + mdImport + ")", 0)

        arcpy.MetadataImporter_conversion (mdImport, target)

        # Edgar's problem line with ImportMetadata tool is below. Not sure why I was even using the ImportMetadata_conversion tool.
        # Seems redundant. Perhaps leftover method from featureclass metadata import.
        #try:
            #arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")
        #    pass

        #except:
        #    PrintMsg("Error updating metadata using template file (" + mdImport + ")", 1)
        #    return True

        # delete the temporary xml metadata file
        if os.path.isfile(mdImport):
            os.remove(mdImport)
            #pass

        # delete metadata tool logs
        logFolder = os.path.dirname(env.scratchFolder)
        logFile = os.path.basename(mdImport).split(".")[0] + "*"

        currentWS = env.workspace
        env.workspace = logFolder
        logList = arcpy.ListFiles(logFile)

        for lg in logList:
            arcpy.Delete_management(lg)

        env.workspace = currentWS

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSoilMap(inputLayer, sdvFolder, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV):
    #
    # Main function
    #
    try:

        global bVerbose
        bVerbose = False   # hard-coded boolean to print diagnostic messages

        # Value cache is a global variable used for fact function which is called by ColorRamp
        global fact_cache
        fact_cache = {}

        # All comppct_r queries have been set to >=

        #sRV = "Relative"  # Low, High


        # Get target gSSURGO database
        global fc, gdb, muDesc, dataType
        muDesc = arcpy.Describe(inputLayer)
        fc = muDesc.catalogPath                         # full path for input mapunit polygon layer
        gdb = os.path.dirname(fc)                       # need to expand to handle featuredatasets
        dataType = muDesc.dataType.lower()

        # Set current workspace to the geodatabase
        env.workspace = gdb
        env.overwriteOutput = True

        # get scratchGDB
        scratchGDB = env.scratchGDB

        # Get dictionary of MUSYM values (optional function for use during development)
        dSymbols = GetMapunitSymbols(gdb)

        # Create list of months for use in some queries
        moList = ListMonths()

        # arcpy.mapping setup
        #
        # Get map document object
        global mxd, df
        mxd = arcpy.mapping.MapDocument("CURRENT")

        # Get active data frame object
        df = mxd.activeDataFrame

        # Dictionary for aggregation method abbreviations
        #
        global dAgg
        dAgg = dict()
        dAgg["Dominant Component"] = "DCP"
        dAgg["Dominant Condition"] = "DCD"
        dAgg["No Aggregation Necessary"] = ""
        dAgg["Percent Present"] = "PP"
        dAgg["Weighted Average"] = "WTA"
        dAgg["Most Limiting"] = "ML"
        dAgg["Least Limiting"] = "LL"


        # Open sdvattribute table and query for [attributename] = sdvAtt
        #dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        #sdvattTable = os.path.join(gdb, "sdvattribute")
        #flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        #sql1 = "attributename = '" + sdvAtt + "'"
        global dSDV
        dSDV = GetSDVAtts(gdb, sdvAtt, aggMethod)

        # Print status
        # Need to modify message when type is Interp and bFuzzy is True
        #
        if aggMethod == "Minimum or Maximum":
            if tieBreaker == dSDV["tiebreakhighlabel"]:
                PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + tieBreaker + " value) using " + os.path.basename(gdb), 0)

            else:
                PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + tieBreaker + " value) using " + os.path.basename(gdb), 0)

        elif dSDV["attributetype"].lower() == "interpretation" and bFuzzy == True:
            PrintMsg(" \nCreating map of '" + sdvAtt + " (weighted average fuzzy value) using " + os.path.basename(gdb), 0)

        else:
            PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + aggMethod.lower() + ") using " + os.path.basename(gdb), 0)

        # Set null replacement values according to SDV rules
        if not dSDV["nullratingreplacementvalue"] is None:
            if dSDV["attributelogicaldatatype"].lower() == "integer":
                nullRating = int(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() == "float":
                nullRating = float(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() in ["string", "choice"]:
                nullRating = dSDV["nullratingreplacementvalue"]

            else:
                nullRating = None

        else:
            nullRating = None

        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        # if dSDV["attributetype"].lower() == "interpretation" and (dSDV["nasisrulename"][0:5] == "NCCPI" or bFuzzy == True):
        #    aggMethod = "Weighted Average"

        if len(dSDV) == 0:
            raise MyError, ""

        # 'Big' 3 tables
        big3Tbls = ["MAPUNIT", "COMPONENT", "CHORIZON"]

        #  Create a dictionary to define minimum field list for the tables being used
        #
        global dFields
        dFields = dict()
        dFields["MAPUNIT"] = ["MUKEY", "MUSYM", "MUNAME", "LKEY"]
        dFields["COMPONENT"] = ["MUKEY", "COKEY", "COMPNAME", "COMPPCT_R"]
        dFields["CHORIZON"] = ["COKEY", "CHKEY", "HZDEPT_R", "HZDEPB_R"]
        dFields["COMONTH"] = ["COKEY", "COMONTHKEY"]
        #dFields["COMONTH"] = ["COMONTHKEY", "MONTH"]

        # Create dictionary containing substitute values for missing data
        global dMissing
        dMissing = dict()
        dMissing["MAPUNIT"] = [None] * len(dFields["MAPUNIT"])
        dMissing["COMPONENT"] = [None] * (len(dFields["COMPONENT"]) - 1)  # adjusted number down because of mukey
        dMissing["CHORIZON"] = [None] * (len(dFields["CHORIZON"]) - 1)
        dMissing["COMONTH"] = [None] * (len(dFields["COMONTH"]) - 1)
        #dMissing["COSOILMOIST"] = [nullRating]
        dMissing[dSDV["attributetablename"].upper()] = [nullRating]
        #PrintMsg(" \ndInitial dMissing values: " + str(dMissing), 0)

        # Dictionary containing sql_clauses for the Big 3
        #
        global dSQL
        dSQL = dict()
        dSQL["MAPUNIT"] = (None, "ORDER BY MUKEY ASC")
        dSQL["COMPONENT"] = (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC")
        dSQL["CHORIZON"] = (None, "ORDER BY COKEY ASC, HZDEPT_R ASC")

        # Get information about the SDV output result field
        resultcolumn = dSDV["resultcolumnname"].upper()

        primaryconcolname = dSDV["primaryconcolname"]
        if primaryconcolname is not None:
            primaryconcolname = primaryconcolname.upper()

        secondaryconcolname = dSDV["secondaryconcolname"]
        if secondaryconcolname is not None:
            secondaryconcolname = secondaryconcolname.upper()

        # Create dictionary to contain key field definitions
        # AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
        # TEXT, FLOAT, DOUBLE, SHORT, LONG, DATE, BLOB, RASTER, GUID
        # field_type, field_length (text only),
        #
        global dFieldInfo
        dFieldInfo = dict()

        # Convert original sdvattribute field settings to ArcGIS data types
        if dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string']:
            #
            dFieldInfo[resultcolumn] = ["TEXT", 254]

        elif dSDV["effectivelogicaldatatype"].lower() == 'vtext':
            #
            dFieldInfo[resultcolumn] = ["TEXT", ""]

        elif dSDV["effectivelogicaldatatype"].lower() == 'float':
            #dFieldInfo[resultcolumn] = ["DOUBLE", ""]
            dFieldInfo[resultcolumn] = ["FLOAT", ""]  # trying to match muaggatt table data type

        elif dSDV["effectivelogicaldatatype"].lower() == 'integer':
            dFieldInfo[resultcolumn] = ["SHORT", ""]

        else:
            raise MyError, "Failed to set dFieldInfo for " + resultcolumn + ", " + dSDV["effectivelogicaldatatype"]

        dFieldInfo["AREASYMBOL"] = ["TEXT", 20]
        dFieldInfo["LKEY"] = ["TEXT", 30]
        dFieldInfo["MUKEY"] = ["TEXT", 30]
        dFieldInfo["MUSYM"] = ["TEXT", 6]
        dFieldInfo["MUNAME"] = ["TEXT", 175]
        dFieldInfo["COKEY"] = ["TEXT", 30]
        dFieldInfo["COMPNAME"] = ["TEXT", 60]
        dFieldInfo["CHKEY"] = ["TEXT", 30]
        dFieldInfo["COMPPCT_R"] = ["SHORT", ""]
        dFieldInfo["HZDEPT_R"] = ["SHORT", ""]
        dFieldInfo["HZDEPB_R"] = ["SHORT", ""]
        #dFieldInfo["INTERPHR"] = ["DOUBLE", ""]
        dFieldInfo["INTERPHR"] = ["FLOAT", ""]  # trying to match muaggatt data type

        if dSDV["attributetype"].lower() == "interpretation" and (bFuzzy == True or dSDV["effectivelogicaldatatype"].lower() == "float"):
            #dFieldInfo["INTERPHRC"] = ["DOUBLE", ""]
            dFieldInfo["INTERPHRC"] = ["FLOAT", ""]

        else:
            dFieldInfo["INTERPHRC"] = ["TEXT", 254]

        dFieldInfo["MONTH"] = ["TEXT", 10]
        dFieldInfo["MONTHSEQ"] = ["SHORT", ""]
        dFieldInfo["COMONTHKEY"] = ["TEXT", 30]
        #PrintMsg(" \nSet final output column '" + resultcolumn + "' to " + str(dFieldInfo[resultcolumn]), 1)
        #PrintMsg(" \nSet initial column 'INTERPHRC' to " + str(dFieldInfo["INTERPHRC"]), 1)



        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        # There is a problem because the XML for the legend does not always match case
        # Create a dictionary as backup, but uppercase and use that to store the original values
        #
        # Assume that data types of string and vtext do not have domains
        global domainValues, domainValuesUp

        if not dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:
            domainValues = GetRatingDomain(gdb)
            #PrintMsg( "\ndomainValues: " + str(domainValues), 1)
            domainValuesUp = [x.upper() for x in domainValues]

        else:
            domainValues = list()
            domainValuesUp = list()


        # Get map legend information from the maplegendxml string
        # For some interps, there are case mismatches with the actual rating values. This
        # problem originates in the Rule Manager. This affects dLegend, legendValues, domainValues, dValues and dLabels.
        # At some point I need to use outputValues to fix these.
        #
        global dLegend

        dLegend = GetMapLegend(dSDV)    # dictionary containing all maplegendxml properties

        global dLabels
        dLabels = dict()

        #PrintMsg(" \nAttributelogicaldatatype: " + dSDV["attributelogicaldatatype"].lower(), 1)

        #if len(dLegend) > 0 and not dSDV["attributelogicaldatatype"].lower() in ["integer", "float"]: # failing on NCCPI here
        if len(dLegend) > 0:
            if not dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
                #
                legendValues = GetValuesFromLegend(dLegend)
                dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext

                if len(domainValues) == 0:
                    for i in range(1, (len(dLabels) + 1)):
                        domainValues.append(dLabels[i]["value"])

            else:
                #PrintMsg(" \n", 1)
                legendValues = GetValuesFromLegend(dLegend)
        else:
            # No map legend information in xml. Must be Progressive or using fuzzy values instead of original classes.
            #
            # This causes a problem for NCCPI.
            #PrintMsg(" \nNo map legend information????", 1)
            #dLabels = dict()
            legendValues = list()  # empty list, no legend
            dLegend["name"] = "Progressive"  # bFuzzy
            dLegend["type"] = "1"

        # If there are no domain values, try using the legend values instead.
        # May want to reconsider this move
        #
        if len(legendValues) > 0:
            if len(domainValues) == 0:
                domainValues = legendValues

        # Create a dictionary based upon domainValues or legendValues.
        # This dictionary will use an uppercase-string version of the original value as the key
        #
        global dValues
        dValues = dict()  # Try creating a new dictionary. Key is uppercase-string value. Value = [order, original value]

        # Some problems with the 'Not rated' data value, legend value and sdvattribute setting ("notratedphrase")
        # No perfect solution.
        #
        # Start by cleaning up the not rated value as best possible
        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False:
            if not dSDV["notratedphrase"] is None:
                # see if the lowercase value is equivalent to 'not rated'
                if dSDV["notratedphrase"].upper() == 'NOT RATED':
                    dSDV["notratedphrase"] = 'Not rated'

                else:
                    dSDV["notratedphrase"] == dSDV["notratedphrase"][0:1].upper() + dSDV["notratedphrase"][1:].lower()

            else:
                dSDV["notratedphrase"] = 'Not rated' # no way to know if this is correct until all of the data has been processed

            #
            # Next see if the not rated value exists in the domain from mdstatdomdet or map legend values
            bNotRated = False

            for d in domainValues:
                if d.upper() == dSDV["notratedphrase"].upper():
                    bNotRated = True

            if bNotRated == False:
                domainValues.insert(0, dSDV["notratedphrase"])

            if dSDV["ruledesign"] == 2:
                # Flip legend (including Not rated) for suitability interps
                domainValues.reverse()
        #
        # Populate dValues dictionary using domainValues
        #
        if len(domainValues) > 0:
            #PrintMsg(" \nIn main, domainValues looks like: " + str(domainValues), 1)

            for val in domainValues:
                #PrintMsg("\tAdding key value (" + val.upper() + ") to dValues dictionary", 1)
                dValues[str(val).upper()] = [len(dValues), val]  # new 02/03

        #PrintMsg(" \ndValues: " + str(dValues), 1)

        # For the result column we need to translate the sdvattribute value to an ArcGIS field data type
        #  'Choice' 'Float' 'Integer' 'string' 'String' 'VText'
        if dSDV["attributelogicaldatatype"].lower() in ['string', 'choice']:
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["TEXT", dSDV["attributefieldsize"]]

        elif dSDV["attributelogicaldatatype"].lower() == "vtext":
            # Not sure if 254 is adequate
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["TEXT", 254]

        elif dSDV["attributelogicaldatatype"].lower() == "integer":
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["SHORT", ""]

        elif dSDV["attributelogicaldatatype"].lower() == "float":
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["FLOAT", dSDV["attributeprecision"]]

        else:
            raise MyError, "Failed to set dFieldInfo for " + dSDV["attributecolumnname"].upper()

        # Identify related tables using mdstatrshipdet and add to tblList
        #
        mdTable = os.path.join(gdb, "mdstatrshipdet")
        mdFlds = ["LTABPHYNAME", "RTABPHYNAME", "LTABCOLPHYNAME", "RTABCOLPHYNAME"]
        level = 0  # table depth
        tblList = list()

        # Make sure mdstatrshipdet table is populated.
        if int(arcpy.GetCount_management(mdTable).getOutput(0)) == 0:
            raise MyError, "Required table (" + mdTable + ") is not populated"

        # Clear previous map layer if it exists
        # Need to change layer file location to "gdb" for final production version
        #
        if dAgg[aggMethod] != "":
            outputLayer = sdvAtt + " " + dAgg[aggMethod]

        else:
            outputLayer = sdvAtt

        if top > 0 or bot > 0:
            outputLayer = outputLayer + ", " + str(top) + " to " + str(bot) + "cm"
            tf = "HZDEPT_R"
            bf = "HZDEPB_R"

            if (bot - top) == 1:
                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

            else:
                #PrintMsg(" \nTesting horizon SQL", 1)
                rng = str(tuple(range(top, (bot + 1))))
                #hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )" # works

                hzQuery = "((" + tf + " BETWEEN " + str(top) + " AND " + str(bot) + " OR " + bf + " BETWEEN " + str(top) + " AND " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )" # test

                #hzQuery = "( " + bf  + " >= " + str(top) + " ) AND (" + tf + " <= " + str(bot) + " )"

        elif secCst != "":
            #PrintMsg(" \nAdding primary and secondary constraint to layer name (" + primCst + " " + secCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst + ", " + secCst

        elif primCst != "":
            #PrintMsg(" \nAdding primaryconstraint to layer name (" + primCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst

        if begMo != "" or endMo != "":
            outputLayer = outputLayer + ", " + str(begMo) + " - " + str(endMo)

        # Check to see if the layer already exists and delete if necessary
        layers = arcpy.mapping.ListLayers(mxd, outputLayer, df)
        if len(layers) == 1:
            arcpy.mapping.RemoveLayer(df, layers[0])

        # Create list of tables in the ArcMap TOC. Later check to see if a table
        # involved in queries needs to be removed from the TOC.
        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)
        mainTables = ['mapunit', 'component', 'chorizon']

        for tv in tableViews:
            if tv.datasetName.lower() in mainTables:
                # Remove this table view from ArcMap that might cause a conflict with queries
                arcpy.mapping.RemoveTableView(df, tv)

        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)   # any other table views...
        rtabphyname = "XXXXX"
        mdSQL = "RTABPHYNAME = '" + dSDV["attributetablename"].lower() + "'"  # initial whereclause for mdstatrshipdet

        # Setup initial queries
        while rtabphyname != "MAPUNIT":
            level += 1

            with arcpy.da.SearchCursor(mdTable, mdFlds, where_clause=mdSQL) as cur:
                # This should only select one record

                for rec in cur:
                    ltabphyname = rec[0].upper()
                    rtabphyname = rec[1].upper()
                    ltabcolphyname = rec[2].upper()
                    rtabcolphyname = rec[3].upper()
                    mdSQL = "RTABPHYNAME = '" + ltabphyname.lower() + "'"
                    if bVerbose:
                        PrintMsg("\tGetting level " + str(level) + " information for " + rtabphyname.upper(), 1)

                    tblList.append(rtabphyname) # save list of tables involved

                    for tv in tableViews:
                        if tv.datasetName.lower() == rtabphyname.lower():
                            # Remove this table view from ArcMap that might cause a conflict with queries
                            arcpy.mapping.RemoveTableView(df, tv)

                    if rtabphyname.upper() == dSDV["attributetablename"].upper():
                        #
                        # This is the table that contains the rating values
                        #
                        # check for primary and secondary restraints
                        # and use a query to apply them if found.

                        # Begin setting up SQL statement for initial filter
                        # This may be changed further down
                        #
                        if dSDV["attributelogicaldatatype"].lower() in ['integer', 'float']:
                            # try to eliminate calculation failures on NULl values
                            try:
                                primSQL = dSDV["attributecolumnname"].upper() + " is not null and " + dSDV["sqlwhereclause"] # sql applied to bottom level table

                            except:
                                primSQL = dSDV["attributecolumnname"].upper() + " is not null"

                        else:
                            try:
                                primSQL = dSDV["sqlwhereclause"]

                            except:
                                primSQL = None

                        if not primaryconcolname is None:
                            # has primary constraint, get primary constraint value
                            if primSQL is None:
                                primSQL = primaryconcolname + " = '" + primCst + "'"

                            else:
                                primSQL = primSQL + " and " + primaryconcolname + " = '" + primCst + "'"

                            if not secondaryconcolname is None:
                                # has primary constraint, get primary constraint value
                                secSQL = secondaryconcolname + " = '" + secCst + "'"
                                primSQL = primSQL + " and " + secSQL
                                #PrintMsg(" \nprimSQL = " + primSQL, 0)

                        if dSDV["attributetablename"].upper() == "COINTERP":

                            #interpSQL = "MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"
                            interpSQL = "RULEDEPTH = 0 AND MRULENAME = '" + dSDV["nasisrulename"] + "'"

                            if primSQL is None:
                                primSQL = interpSQL
                                #primSQL = "MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"

                            else:
                                #primSQL = primSQL + " and MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"
                                primSQL = interpSQL + " AND " + primSQL

                            # Try populating the cokeyList variable here and use it later in ReadTable
                            cokeyList = list()

                        elif dSDV["attributetablename"].upper() == "CHORIZON":
                            if primSQL is None:
                                primSQL = hzQuery

                            else:
                                primSQL = primSQL + " and " + hzQuery

                        elif dSDV["attributetablename"].upper() == "CHUNIFIED":
                            if primSQL is None:
                                primSQL = primSQL + " and RVINDICATOR = 'Yes'"

                            else:
                                primSQL = "CHUNIFIED.RVINDICATOR = 'Yes'"

                        elif dSDV["attributetablename"].upper() == "COMONTH":
                            if primSQL is None:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = "(MONTHSEQ = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = "(MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            else:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = primSQL + " AND (MONTHSEQ = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = primSQL + " AND (MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                        elif dSDV["attributetablename"].upper() == "COSOILMOIST":
                            # Having problems with NULL values for some months. Need to retain NULL values with query,
                            # but then substitute 201cm in ReadTable
                            #
                            primSQL = dSDV["sqlwhereclause"]


                        if primSQL is None:
                            primSQL = ""

                        if bVerbose:
                            PrintMsg("\tRating table (" + rtabphyname.upper() + ") SQL: " + primSQL, 1)

                        # Create list of necessary fields

                        # Get field list for mapunit or component or chorizon
                        if rtabphyname in big3Tbls:
                            flds = dFields[rtabphyname]
                            if not dSDV["attributecolumnname"].upper() in flds:
                                flds.append(dSDV["attributecolumnname"].upper())

                            dFields[rtabphyname] = flds
                            dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)

                        else:
                            # Not one of the big 3 tables, just use foreign key and sdvattribute column
                            flds = [rtabcolphyname, dSDV["attributecolumnname"].upper()]
                            dFields[rtabphyname] = flds

                            if not rtabphyname in dMissing:
                                dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)
                                #PrintMsg("\nSetting missing fields for " + rtabphyname + " to " + str(dMissing[rtabphyname]), 1)

                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # For tables other than the primary ones.
                            sql = (None, None)

                        if rtabphyname == "MAPUNIT" and aggMethod != "No Aggregation Necessary":
                            # No aggregation necessary?
                            dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dMapunit) == 0:
                                raise MyError, "No m data for " + sdvAtt

                        elif rtabphyname == "COMPONENT":
                            #if cutOff is not None:
                            if dSDV["sqlwhereclause"] is not None:
                                if cutOff == 0:
                                    # Having problems with CONUS database. Including COMPPCT_R in the
                                    # where_clause is returning zero records. Found while testing Hydric map. Is a Bug?
                                    # Work around is to put COMPPCT_R part of query last in the string

                                    primSQL =  dSDV["sqlwhereclause"]

                                else:
                                    primSQL = dSDV["sqlwhereclause"] + ' AND "COMPPCT_R" >= ' + str(cutOff)

                            else:
                                primSQL = "COMPPCT_R >= " + str(cutOff)


                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dComponent) == 0:
                                raise MyError, "No component data for " + sdvAtt

                        elif rtabphyname == "CHORIZON":
                            #primSQL = "(CHORIZON.HZDEPT_R between " + str(top) + " and " + str(bot) + " or CHORIZON.HZDEPB_R between " + str(top) + " and " + str(bot + 1) + ")"
                            #PrintMsg(" \nhzQuery: " + hzQuery, 1)
                            dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)

                            if len(dHorizon) == 0:
                                raise MyError, "No horizon data for " + sdvAtt

                        else:
                            # This should be the bottom-level table containing the requested data
                            #
                            cokeyList = list()  # Try using this to pare down the COINTERP table record count
                            #cokeyList = dComponent.keys()  # Won't work. dComponent isn't populated yet

                            dTbl = ReadTable(dSDV["attributetablename"].upper(), flds, primSQL, level, sql)

                            if len(dTbl) == 0:
                                raise MyError, " \nNo " + dSDV["attributetablename"] + " data for " + sdvAtt

                    else:
                        # Bottom section
                        #
                        # This is one of the intermediate tables
                        # Create list of necessary fields
                        # Get field list for mapunit or component or chorizon
                        #
                        flds = dFields[rtabphyname]
                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # This needs to be fixed. I have a whereclause in the try and an sqlclause in the except.
                            sql = (None, None)

                        primSQL = ""
                        #PrintMsg(" \n\tReading intermediate table: " + rtabphyname + "   sql: " + str(sql), 1)

                        if rtabphyname == "MAPUNIT":
                            dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "COMPONENT":
                            primSQL = "COMPPCT_R >= " + str(cutOff)

                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "CHORIZON":
                            #primSQL = "(CHORIZON.HZDEPT_R between " + str(top) + " and " + str(bot) + " or CHORIZON.HZDEPB_R between " + str(top) + " and " + str(bot + 1) + ")"
                            tf = "HZDEPT_R"
                            bf = "HZDEPB_R"
                            #primSQL = "( ( " + tf + " between " + str(top) + " and " + str(bot - 1) + " or " + bf + " between " + str(top) + " and " + str(bot) + " ) or " + \
                            #"( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"
                            if (bot - top) == 1:
                                #rng = str(tuple(range(top, (bot + 1))))
                                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            else:
                                rng = str(tuple(range(top, bot)))
                                hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            #PrintMsg(" \nSetting primSQL for when rtabphyname = 'CHORIZON' to: " + hzQuery, 1)
                            dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)

                        elif rtabphyname == "COMONTH":

                            # Need to look at the SQL for the other tables as well...
                            if begMo == endMo:
                                # query for single month
                                primSQL = "(MONTHSEQ = " + str(moList.index(begMo)) + ")"

                            else:
                                primSQL = "(MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            #PrintMsg(" \nIntermediate SQL: " + primSQL, 1)
                            dMonth = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dMonth) == 0:
                                raise MyError, "No month data for " + sdvAtt + " \n "
                            #else:
                            #    PrintMsg(" \nFound " + str(len(dMonth)) + " records in COMONTH", 1)

                        else:
                            PrintMsg(" \n\tUnable to read data from: " + rtabphyname, 1)


            if level > 6:
                raise MyError, "Failed to get table relationships"


        # Create a list of all fields needed for the initial output table. This
        # one will include primary keys that won't be in the final output table.
        #
        if len(tblList) == 0:
            # No Aggregation Necessary, append field to mapunit list
            tblList = ["MAPUNIT"]
            if dSDV["attributecolumnname"].upper() in dFields["MAPUNIT"]:
                PrintMsg(" \nSkipping addition of field "  + dSDV["attributecolumnname"].upper(), 1)

            else:
                dFields["MAPUNIT"].append(dSDV["attributecolumnname"].upper())

        tblList.reverse()  # Set order of the tables so that mapunit is on top

        if bVerbose:
            PrintMsg(" \nUsing these tables: " + ", ".join(tblList), 1)

        # Create a list of all fields to be used
        global allFields
        allFields = ["AREASYMBOL"]
        allFields.extend(dFields["MAPUNIT"])  # always include the selected set of fields from mapunit table
        #PrintMsg(" \nallFields 1: " + ", ".join(allFields), 1)

        # Substitute resultcolumname for last field in allFields
        for tbl in tblList:
            tFields = dFields[tbl]
            for fld in tFields:
                if not fld.upper() in allFields:
                    #PrintMsg("\tAdding " + tbl + "." + fld.upper(), 1)
                    allFields.append(fld.upper())

        if not dSDV["attributecolumnname"].upper() in allFields:
            allFields.append(dSDV["attributecolumnname"].upper())

        #PrintMsg(" \nallFields 3: " + ", ".join(allFields), 1)

        # Create initial output table (one-to-many)
        # Now created with resultcolumnname
        #
        initialTbl = CreateInitialTable(gdb, allFields, dFieldInfo)

        if initialTbl is None:
            raise MyError, "Failed to create initial query table"

        # Create dictionary for areasymbol
        #PrintMsg(" \nGetting polygon count...", 1)
        global polyCnt, fcCnt
        polyCnt = int(arcpy.GetCount_management(inputLayer).getOutput(0))  # featurelayer polygon count
        fcCnt = int(arcpy.GetCount_management(fc).getOutput(0))            # featureclass polygon count
        #PrintMsg(" \nGot polygon count of " + Number_Format(polyCnt, 0, True), 1)

        # Getting Areasymbols and legendkeys is a bottleneck (Thursday Aug 18). Any room for improvement?
        #
        #PrintMsg(" \nGetting areasymbols...", 1)
        global dAreasymbols
        dAreasymbols = GetAreasymbols(gdb)

        if len(dAreasymbols) == 0:
            raise MyError, ""

        # Made changes in the table relates code that creates tblList. List now has MAPUNIT in first position
        #

        if tblList == ['MAPUNIT']:
            # No aggregation needed
            if CreateRatingTable1(tblList, dSDV["attributetablename"].upper(), initialTbl, dAreasymbols) == False:
                raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT']:
            if CreateRatingTable2(tblList, dSDV["attributetablename"].upper(), dComponent, initialTbl) == False:
                raise MyError, ""
            del dComponent

        elif tblList == ['MAPUNIT', 'COMPONENT', 'CHORIZON']:
            if CreateRatingTable3(tblList, dSDV["attributetablename"].upper(), dComponent, dHorizon, initialTbl) == False:
                raise MyError, ""
            del dComponent, dHorizon

        elif tblList == ['MAPUNIT', 'COMPONENT', 'CHORIZON', dSDV["attributetablename"].upper()]:
            # COMPONENT, CHORIZON, CHTEXTUREGRP
            if CreateRatingTable3S(tblList, dSDV["attributetablename"].upper(), dComponent, dHorizon, dTbl, initialTbl) == False:
                raise MyError, ""
            del dComponent, dHorizon

        elif tblList in [['MAPUNIT', "MUAGGATT"], ['MAPUNIT', "MUCROPYLD"]]:
            if CreateRatingTable1S(tblList, dSDV["attributetablename"].upper(), dTbl, initialTbl, dAreasymbols) == False:
                raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT', dSDV["attributetablename"].upper()]:
            if dSDV["attributetablename"].upper() == "COINTERP":
                if CreateRatingInterps(tblList, dSDV["attributetablename"].upper(), dComponent, dTbl, initialTbl) == False:
                    raise MyError, ""
                del dComponent

            else:
                if CreateRatingTable2S(tblList, dSDV["attributetablename"].upper(), dComponent, dTbl, initialTbl) == False:
                    raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT', 'COMONTH', 'COSOILMOIST']:
            if dSDV["attributetablename"].upper() == "COSOILMOIST":

                #PrintMsg(" \ndMissing values before CreateSoilMoistureTable: " + str(dMissing))

                if CreateSoilMoistureTable(tblList, dSDV["attributetablename"].upper(), dComponent, dMonth, dTbl, initialTbl, begMo, endMo) == False:
                    raise MyError, ""
                del dMonth, dComponent # trying to lower memory usage

            else:
                PrintMsg(" \nCannot handle table:" + dSDV["attributetablename"].upper(), 1)
                raise MyError, "Tables Bad Combo: " + str(tblList)

        else:
            # Need to add ['COMPONENT', 'COMONTH', 'COSOILMOIST']
            raise MyError, "Problem with list of input tables: " + str(tblList)

        # **************************************************************************
        # Look at attribflags and apply the appropriate aggregation function

        if not arcpy.Exists(initialTbl):
            # Output table was not created. Exit program.
            raise MyError, ""

        #PrintMsg(" \ninitialTbl has " + arcpy.GetCount_management(initialTbl).getOutput(0) + " records", 1)

        if int(arcpy.GetCount_management(initialTbl).getOutput(0)) == 0:
            #
            raise MyError, "Failed to populate query table"

        # Proceed with aggregation if the intermediate table has data.
        # Add result column to fields list
        iFlds = len(allFields)
        newField = dSDV["resultcolumnname"].upper()

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)
        allFields[len(allFields) - 1] = newField
        rmFields = ["MUSYM", "COMPNAME", "LKEY"]
        for fld in rmFields:
            if fld in allFields:
                allFields.remove(fld)

        if newField == "MUNAME":
            allFields.remove("MUNAME")

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)

        # Create name for final output table that will be saved to the input gSSURGO database
        #
        global tblName

        if dAgg[aggMethod] == "":
            # No aggregation method necessary
            tblName = "SDV_" + dSDV["resultcolumnname"]

        else:
            if secCst != "":
                tblName = "SDV_" + dSDV["resultcolumnname"]  + "_" + primCst.replace(" ", "_") + "_" + secCst.replace(" ", "_")

            elif primCst != "":
                tblName = "SDV_" + dSDV["resultcolumnname"] + "_" + primCst.replace(" ", "_")

            elif top > 0 or bot > 0:
                tblName = "SDV_" + dSDV["resultcolumnname"] + "_" + str(top) + "to" + str(bot)

            else:
                tblName = "SDV_" + dSDV["resultcolumnname"]

        # **************************************************************************
        #
        # Aggregation Logic to determine which functions will be used to process the
        # intermediate table and produce the final output table.
        #
        # This is where outputValues is set
        #
        if dSDV["attributetype"] == "Property":
            # These are all Soil Properties

            if dSDV["mapunitlevelattribflag"] == 1:
                # This is a Map unit Level Soil Property
                #PrintMsg("Map unit level, no aggregation neccessary", 1)
                outputTbl, outputValues = Aggregate1(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

            elif dSDV["complevelattribflag"] == 1:

                if dSDV["horzlevelattribflag"] == 0:
                    # These are Component Level-Only Soil Properties

                    if dSDV["cmonthlevelattribflag"] == 0:
                        #
                        #  These are Component Level Soil Properties

                        if aggMethod == "Dominant Component":
                            #PrintMsg(" \n1. domainValues: " + ", ".join(domainValues), 1)
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Minimum or Maximum":
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Dominant Condition":
                            if bVerbose:
                                PrintMsg(" \nDomain Values are now: " + str(domainValues), 1)

                            if len(domainValues) > 0 and dSDV["tiebreakdomainname"] is not None :
                                if bVerbose:
                                    PrintMsg(" \n1. aggMethod = " + aggMethod + " and domainValues = " + str(domainValues), 1)
                                outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #PrintMsg(" \nOuputValues: " + str(outputValues), 1)

                            else:
                                if bVerbose:
                                    PrintMsg(" \n2. aggMethod = " + aggMethod + " and no domainValues", 1)

                                outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Minimum or Maximum":
                            #
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Weighted Average" and dSDV["attributetype"].lower() == "property":
                            # Using NCCPI for any numeric component level value?
                            # This doesn't seem to be working for Range Prod 2016-01-28
                            #
                            outputTbl, outputValues = AggregateCo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)

                        elif aggMethod == "Weighted Average" and SDV["attributetype"].lower() == "intepretation":
                            # Using NCCPI for any numeric component level value?
                            # This doesn't seem to be working for Range Prod 2016-01-28
                            #
                            #PrintMsg(" \nNCCPI WTA using Aggregate2_NCCPI function", 1)
                            outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Percent Present":
                            # This is Hydric?
                            outputTbl, outputValues = AggregateCo_PP_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            # Don't know what kind of interp this is
                            raise MyError, "5. Component aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


                    elif dSDV["cmonthlevelattribflag"] == 1:
                        #
                        # These are Component-Month Level Soil Properties
                        #
                        if dSDV["resultcolumnname"].startswith("Dep2WatTbl"):
                            #PrintMsg(" \nThis is Depth to Water Table (" + dSDV["resultcolumnname"] + ")", 1)

                            if aggMethod == "Dominant Component":
                                outputTbl, outputValues = AggregateCo_DCP_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Dominant Condition":
                                outputTbl, outputValues = AggregateCo_Mo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #raise MyError, "EARLY OUT"

                            elif aggMethod == "Weighted Average":
                                outputTbl, outputValues = AggregateCo_WTA_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                # Component-Month such as depth to water table - Minimum or Maximum
                                outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #raise MyError, "5. Component-comonth aggregation method has not yet been developed "

                        else:
                            # This will be flooding or ponding frequency. In theory these should be the same value
                            # for each month because these are normally annual ratings
                            #
                            # PrintMsg(" \nThis is Flooding or Ponding (" + dSDV["resultcolumnname"] + ")", 1 )
                            #
                            if aggMethod == "Dominant Component":
                                # Problem with this aggregation method (AggregateCo_DCP). The CompPct sum is 12X because of the months.
                                outputTbl, outputValues = AggregateCo_Mo_DCP_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Dominant Condition":
                                # Problem with this aggregation method (AggregateCo_DCP_Domain). The CompPct sum is 12X because of the months.
                                outputTbl, outputValues = AggregateCo_Mo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl) # Orig
                                #PrintMsg(" \noutputValues: " + ", ".join(outputValues), 1)

                            elif aggMethod == "Minimum or Maximum":
                                outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Weighted Average":
                              outputTbl, outputValues = AggregateCo_Mo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                raise MyError, "Aggregation method: " + aggMethod + "; attibute " + dSDV["attributecolumnname"].upper()

                    else:
                        raise MyError, "Attribute level flag problem"

                elif dSDV["horzlevelattribflag"] == 1:
                    # These are all Horizon Level Soil Properties

                    if aggMethod == "Weighted Average":
                        # component aggregation is weighted average

                        if dSDV["attributelogicaldatatype"].lower() in ["integer", "float"]:
                            # Just making sure that these are numeric values, not indexes
                            if dSDV["horzaggmeth"] == "Weighted Average":
                                # Use weighted average for horizon data (works for AWC)
                                outputTbl, outputValues = AggregateHz_WTA_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif dSDV["horzaggmeth"] == "Weighted Sum":
                                # Calculate sum for horizon data (egs. AWS)
                                outputTbl, outputValues = AggregateHz_WTA_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "12. Weighted Average not appropriate for " + dataType

                    elif aggMethod == "Dominant Component":
                        # Need to find or build this function

                        if sdvAtt.startswith("Surface") or sdvAtt.endswith("(Surface)"):
                            #
                            # I just added this on Monday to fix problem with Surface Texture DCP
                            # Need to test
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["effectivelogicaldatatype"].lower() == "choice":
                            # Indexed value such as kFactor, cannot use weighted average
                            # for horizon properties
                            #outputTbl, outputValues = AggregateCo_DCP_Domain(gdb, sdvAtt,dSDV["attributecolumnname"].upper(), aggMethod, initialTbl)
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt,dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["horzaggmeth"] == "Weighted Average":
                            #PrintMsg(" \nHorizon aggregation method = WTA and attributelogical datatype = " + dSDV["attributelogicaldatatype"].lower(), 1)
                            outputTbl, outputValues = AggregateHz_DCP_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "9. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

                    elif aggMethod == "Dominant Condition":

                        if sdvAtt.startswith("Surface") or sdvAtt.endswith("(Surface)"):
                            if dSDV["effectivelogicaldatatype"].lower() == "choice":
                                if bVerbose:
                                    PrintMsg(" \nDominant condition for surface-level attribute", 1)
                                outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)


                        elif dSDV["effectivelogicaldatatype"].lower() in ("float", "integer"):
                            # Dominant condition for a horizon level numeric value is probably not a good idea
                            outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["effectivelogicaldatatype"].lower() == "choice" and dSDV["tiebreakdomainname"] is not None:
                            # KFactor (Indexed values)
                            #if bVerbose:
                            #PrintMsg(" \nDominant condition for choice type", 1)
                            outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "No aggregation calculation selected for DCD"

                    elif aggMethod == "Minimum or Maximum":
                        # Need to figure out aggregation method for horizon level  max-min
                        if dSDV["effectivelogicaldatatype"].lower() == "choice":
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)

                        else:  # These should be numeric, probably need to test here.
                            outputTbl, outputValues = AggregateHz_MaxMin_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                    else:
                        raise MyError, "'" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

                else:
                    raise MyError, "Horizon-level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

            else:
                # Should never hit this
                raise MyError, "Unknown depth level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

        elif dSDV["attributetype"].lower() == "interpretation":

            #PrintMsg(" \nDo I need to populate interp rating class values here, before aggregation?", 1)
            #PrintMsg(" \ndomainValues:" + str(domainValues), 1)

            if len(domainValues) == 0 and "label" in dLegend:
                # create fake domain using map legend labels and hope they are correct
                labelValues = dLegend["labels"]

                for i in range(1, (len(labelValues) + 1)):
                    domainValues.append(labelValues[i])


            if not 'Not rated' in domainValues and len(domainValues) > 0:
                # These are all Soil Interpretations
                domainValues.insert(0, "Not rated")


            if dSDV["ruledesign"] == 1:
                #
                # This is a Soil Interpretation for Limitations or Risk

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    #PrintMsg(" \nInterpretation; aggMethod = " + aggMethod, 1)
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float':
                    # Map fuzzy values for interps
                    #PrintMsg(" \nNCCPI WTA using Aggregate2_NCCPI function", 1)
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:

                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    #PrintMsg(" \nmapunitlevelattribflag: " + str(dSDV["mapunitlevelattribflag"]) + ", complevelattribflag: " + str(dSDV["complevelattribflag"]) + ", cmonthlevelattribflag: " + str(dSDV["cmonthlevelattribflag"]) + ", horzlevelattribflag: " + str(dSDV["horzlevelattribflag"]) + ", effectivelogicaldatatype: " + dSDV["effectivelogicaldatatype"], 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

            elif dSDV["ruledesign"] == 2:
                # This is a Soil Interpretation for Suitability

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)  # changed this for Sand Suitability

                elif bFuzzy or (aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float'):
                    # This is NCCPI
                    #PrintMsg(" \nA Aggregate2_NCCPI", 1)
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    # Friday problem here for NCCPI
                    #PrintMsg(" \n" + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


            elif dSDV["ruledesign"] == 3:
                # This is a Soil Interpretation for Class. Only a very few interps in the nation use this.
                # Such as MO- Pasture hayland; MT-Conservation Tree Shrub Groups; CA- Revised Storie Index

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float':
                    # This is NCCPI?
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    #PrintMsg(" \nNot sure about aggregation method for ruledesign = 3", 1)
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    PrintMsg(" \nRuledesign 3: " + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Interp aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


            elif dSDV["ruledesign"] is None:
                # This is a Soil Interpretation???
                raise MyError, "Soil Interp with no RuleDesign setting"

            else:
                raise MyError, "No aggregation calculation selected 10"

        else:
            raise MyError, "Invalid SDV AttributeType: " + str(dSDV["attributetype"])

        # quit if no data is available for selected property or interp
        if len(outputValues) == 0 or (len(outputValues) == 1 and (outputValues[0] == None or outputValues[0] == "")):
            raise MyError, "No data available for '" + sdvAtt + "'"
            #PrintMsg("No data available for '" + sdvAtt + "'", 1)

        if BadTable(outputTbl):
            raise MyError, "No data available for '" + sdvAtt + "'"

        #if not bVerbose:
            # delete sdv_initial table
            #arcpy.Delete_management(initialTbl)


        #
        # End of Aggregation Logic and Data Processing
        # **************************************************************************
        # **************************************************************************
        #


        # **************************************************************************
        # **************************************************************************
        #
        # Symbology Code Begins Below
        #
        #
        if bVerbose:
            PrintMsg(" \noutputValues: " + str(outputValues) + " \n ", 1)

            for param in sorted(dSDV):
                setting = dSDV[param]

                if not param in ["attributedescription", "maplegendxml"]:
                    PrintMsg("\t" + param + ":\t" + str(setting), 1)

            PrintMsg(" \n", 0)

        if outputValues == [-999999999, 999999999]:
            raise MyError, "We have an outputValues problem"


        # Adding new code on 2017-07-27 to try and address case mismatches between data and map legend values
        # This affects dLegend, legendValues, domainValues, dValues and dLabels.

        if bVerbose:
            try:
                PrintMsg(" \n" + dSDV["attributename"] + "; MapLegendKey: " + dLegend["maplegendkey"] + "; Type: " + dLegend["type"] + " \n ", 1)

            except:
                # Is dLegend populated??
                pass


        if dSDV["effectivelogicaldatatype"] != 'float' and "labels" in dLegend:
            # NCCPI v2 is failing here since it does not have dLegend["labels"]. Should I be skipping effectivelogicaldatatype == 'float'???
            arcpy.SetProgressorLabel("Getting map legend information")
            # Fix dLegend first
            dLabels = dLegend["labels"]   # NCCPI version 2 is failing here
            end = len(dLabels) + 1

            try:

                for i in range(1, end):
                    labelInfo = dLabels[i]
                    order = labelInfo["order"]
                    value = labelInfo["value"]
                    label = labelInfo["label"]

                    if value.upper() in dValues:
                        # Compare value to outputValues
                        for dataValue in outputValues:
                            if dataValue.upper() == value.upper():
                                value = dataValue
                                labelInfo["value"] = value
                                dLabels[i] = labelInfo

                dLegend["labels"] = dLabels

            except:
                pass

                # Fix domainValues
                try:

                    for dv in domainValues:
                        for dataValue in outputValues:

                            if dataValue.upper() == dv.upper() and dataValue != dv:
                                indx = domainValues.index(dv)
                                junk = domainValues.pop(indx)
                                domainValues.insert(indx, dataValue)

                except:
                    pass

                # Fix dValues
                try:
                    for key, val in dValues.items():
                        seq, dv = val

                        for dataValue in outputValues:

                            if dataValue.upper() == key and dataValue != dv:
                                indx = domainValues.index(dv)
                                junk = domainValues.pop(indx)
                                val =[seq, dataValue]
                                dValues[key] = val

                except:
                    pass

            #
            # End of case-mismatch code


        #PrintMsg(" \nLegend name in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)

        if dLegend["name"] != "Random" and muDesc.dataType.lower() == "featurelayer":
            #PrintMsg(" \nLegend name 1 in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)
            #PrintMsg(" \nChecking dLegend contents: " + str(dLegend), 1)

            global dLayerDefinition
            if not "labels" in dLegend:
                #PrintMsg(" \nCould we use ClassBreaksJSON here?", 1)
                dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"])


            else:
                dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"])


        else:
            # Create empty legend dictionary so that CreateMapLayer function will run for Random Color legend
            dLayerDefinition = dict()

        # Create map layer with join using arcpy.mapping
        # sdvAtt, aggMethod, inputLayer
        if arcpy.Exists(outputTbl):
            global tblDesc
            tblDesc = arcpy.Describe(outputTbl)

            #PrintMsg(" \nCreating layer file for " + outputLayer + "....", 0)
            outputLayerFile = os.path.join(os.path.dirname(gdb), os.path.basename(outputLayer.replace(", ", "_").replace(" ", "_")) + ".lyr")

            # Save parameter settings for layer description
            if not dSDV["attributeuom"] is None:
                parameterString = "Units of Measure: " +  dSDV["attributeuom"]
                parameterString = parameterString + "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

            else:
                parameterString = "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

            if primCst != "":
                parameterString = parameterString + "\r\n" + dSDV["primaryconstraintlabel"] + ": " + primCst

            if secCst != "":
                parameterString = parameterString + "; " + dSDV["secondaryconstraintlabel"] + ": " + secCst

            if dSDV["horzlevelattribflag"]:
                parameterString = parameterString + "\r\nTop horizon depth: " + str(top)
                parameterString = parameterString + ";  " + "Bottom horizon depth: " + str(bot)

            elif dSDV["cmonthlevelattribflag"]:
                parameterString = parameterString + "\r\nMonths: " + begMo + " through " + endMo

            if cutOff is not None:
                parameterString = parameterString + "\r\nComponent Percent Cutoff:  " + str(cutOff) + "%"

            if dSDV["effectivelogicaldatatype"].lower() in ["float", "integer"]:
                parameterString = parameterString + "\r\nUsing " + sRV.lower() + " values (" + dSDV["attributecolumnname"] + ") from " + dSDV["attributetablename"].lower() + " table"

            # Finish adding system information to description
            #
            #
            envUser = arcpy.GetSystemEnvironment("USERNAME")
            if "." in envUser:
                user = envUser.split(".")
                userName = " ".join(user).title()

            elif " " in envUser:
                user = envUser.split(" ")
                userName = " ".join(user).title()

            else:
                userName = envUser

            parameterString = parameterString + "\r\nGeoDatabase: " + os.path.dirname(fc) + "\r\n" + muDesc.dataType.title() + ": " + \
            os.path.basename(fc) + "\r\nRating Table: " + os.path.basename(outputTbl) + \
            "\r\nLayer File: " + outputLayerFile + \
            "\r\nCreated by " + userName + " on " + datetime.date.today().isoformat() + " using script " + os.path.basename(sys.argv[0])

            if arcpy.Exists(outputLayerFile):
                arcpy.Delete_management(outputLayerFile)

            # Create metadata for outputTbl
            bMetadata = UpdateMetadata(gdb, outputTbl, parameterString)

            if bMetadata == False:
                PrintMsg(" \nFailed to update layer and table metadata", 1)

            if muDesc.dataType.lower() == "featurelayer":
                #PrintMsg(" \ndLayerDefinition has " + str(len(dLayerDefinition)) + " items", 1)
                bMapLayer = CreateMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, dLayerDefinition)  # missing dLayerDefinition
                #PrintMsg(" \nFinished '" + sdvAtt + "' (" + aggMethod.lower() + ") for " + os.path.basename(gdb) + " \n ", 0)



            elif muDesc.dataType.lower() == "rasterlayer":
                bMapLayer = CreateRasterMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString)

            del mxd

            return True

        else:
            raise MyError, "Failed to create summary table and map layer \n "


    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSoilMap_Bak(inputLayer, sdvFolder, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV):
    #
    # Main function
    #
    try:

        global bVerbose
        bVerbose = False   # hard-coded boolean to print diagnostic messages

        # Value cache is a global variable used for fact function which is called by ColorRamp
        global fact_cache
        fact_cache = {}

        # All comppct_r queries have been set to >=

        #sRV = "Relative"  # Low, High


        # Get target gSSURGO database
        global fc, gdb, muDesc, dataType
        muDesc = arcpy.Describe(inputLayer)
        fc = muDesc.catalogPath                         # full path for input mapunit polygon layer
        gdb = os.path.dirname(fc)                       # need to expand to handle featuredatasets
        dataType = muDesc.dataType.lower()

        # Set current workspace to the geodatabase
        env.workspace = gdb
        env.overwriteOutput = True

        # get scratchGDB
        scratchGDB = env.scratchGDB

        # Get dictionary of MUSYM values (optional function for use during development)
        dSymbols = GetMapunitSymbols(gdb)

        # Create list of months for use in some queries
        moList = ListMonths()

        # arcpy.mapping setup
        #
        # Get map document object
        global mxd, df
        mxd = arcpy.mapping.MapDocument("CURRENT")

        # Get active data frame object
        df = mxd.activeDataFrame

        # Dictionary for aggregation method abbreviations
        #
        global dAgg
        dAgg = dict()
        dAgg["Dominant Component"] = "DCP"
        dAgg["Dominant Condition"] = "DCD"
        dAgg["No Aggregation Necessary"] = ""
        dAgg["Percent Present"] = "PP"
        dAgg["Weighted Average"] = "WTA"
        dAgg["Most Limiting"] = "ML"
        dAgg["Least Limiting"] = "LL"


        # Open sdvattribute table and query for [attributename] = sdvAtt
        #dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        #sdvattTable = os.path.join(gdb, "sdvattribute")
        #flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        #sql1 = "attributename = '" + sdvAtt + "'"
        global dSDV
        dSDV = GetSDVAtts(gdb, sdvAtt, aggMethod)

        # Print status
        # Need to modify message when type is Interp and bFuzzy is True
        #
        if aggMethod == "Minimum or Maximum":
            if tieBreaker == dSDV["tiebreakhighlabel"]:
                PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + tieBreaker + " value) using " + os.path.basename(gdb), 0)

            else:
                PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + tieBreaker + " value) using " + os.path.basename(gdb), 0)

        elif dSDV["attributetype"].lower() == "interpretation" and bFuzzy == True:
            PrintMsg(" \nCreating map of '" + sdvAtt + " (weighted average fuzzy value) using " + os.path.basename(gdb), 0)

        else:
            PrintMsg(" \nCreating map of '" + sdvAtt + "' (" + aggMethod.lower() + ") using " + os.path.basename(gdb), 0)

        # Set null replacement values according to SDV rules
        if not dSDV["nullratingreplacementvalue"] is None:
            if dSDV["attributelogicaldatatype"].lower() == "integer":
                nullRating = int(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() == "float":
                nullRating = float(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() in ["string", "choice"]:
                nullRating = dSDV["nullratingreplacementvalue"]

            else:
                nullRating = None

        else:
            nullRating = None

        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        # if dSDV["attributetype"].lower() == "interpretation" and (dSDV["nasisrulename"][0:5] == "NCCPI" or bFuzzy == True):
        #    aggMethod = "Weighted Average"

        if len(dSDV) == 0:
            raise MyError, ""

        # 'Big' 3 tables
        big3Tbls = ["MAPUNIT", "COMPONENT", "CHORIZON"]

        #  Create a dictionary to define minimum field list for the tables being used
        #
        global dFields
        dFields = dict()
        dFields["MAPUNIT"] = ["MUKEY", "MUSYM", "MUNAME", "LKEY"]
        dFields["COMPONENT"] = ["MUKEY", "COKEY", "COMPNAME", "COMPPCT_R"]
        dFields["CHORIZON"] = ["COKEY", "CHKEY", "HZDEPT_R", "HZDEPB_R"]
        dFields["COMONTH"] = ["COKEY", "COMONTHKEY"]
        #dFields["COMONTH"] = ["COMONTHKEY", "MONTH"]

        # Create dictionary containing substitute values for missing data
        global dMissing
        dMissing = dict()
        dMissing["MAPUNIT"] = [None] * len(dFields["MAPUNIT"])
        dMissing["COMPONENT"] = [None] * (len(dFields["COMPONENT"]) - 1)  # adjusted number down because of mukey
        dMissing["CHORIZON"] = [None] * (len(dFields["CHORIZON"]) - 1)
        dMissing["COMONTH"] = [None] * (len(dFields["COMONTH"]) - 1)
        #dMissing["COSOILMOIST"] = [nullRating]
        dMissing[dSDV["attributetablename"].upper()] = [nullRating]
        #PrintMsg(" \ndInitial dMissing values: " + str(dMissing), 0)

        # Dictionary containing sql_clauses for the Big 3
        #
        global dSQL
        dSQL = dict()
        dSQL["MAPUNIT"] = (None, "ORDER BY MUKEY ASC")
        dSQL["COMPONENT"] = (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC")
        dSQL["CHORIZON"] = (None, "ORDER BY COKEY ASC, HZDEPT_R ASC")

        # Get information about the SDV output result field
        resultcolumn = dSDV["resultcolumnname"].upper()

        primaryconcolname = dSDV["primaryconcolname"]
        if primaryconcolname is not None:
            primaryconcolname = primaryconcolname.upper()

        secondaryconcolname = dSDV["secondaryconcolname"]
        if secondaryconcolname is not None:
            secondaryconcolname = secondaryconcolname.upper()

        # Create dictionary to contain key field definitions
        # AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
        # TEXT, FLOAT, DOUBLE, SHORT, LONG, DATE, BLOB, RASTER, GUID
        # field_type, field_length (text only),
        #
        global dFieldInfo
        dFieldInfo = dict()

        # Convert original sdvattribute field settings to ArcGIS data types
        if dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string']:
            #
            dFieldInfo[resultcolumn] = ["TEXT", 254]

        elif dSDV["effectivelogicaldatatype"].lower() == 'vtext':
            #
            dFieldInfo[resultcolumn] = ["TEXT", ""]

        elif dSDV["effectivelogicaldatatype"].lower() == 'float':
            #dFieldInfo[resultcolumn] = ["DOUBLE", ""]
            dFieldInfo[resultcolumn] = ["FLOAT", ""]  # trying to match muaggatt table data type

        elif dSDV["effectivelogicaldatatype"].lower() == 'integer':
            dFieldInfo[resultcolumn] = ["SHORT", ""]

        else:
            raise MyError, "Failed to set dFieldInfo for " + resultcolumn + ", " + dSDV["effectivelogicaldatatype"]

        dFieldInfo["AREASYMBOL"] = ["TEXT", 20]
        dFieldInfo["LKEY"] = ["TEXT", 30]
        dFieldInfo["MUKEY"] = ["TEXT", 30]
        dFieldInfo["MUSYM"] = ["TEXT", 6]
        dFieldInfo["MUNAME"] = ["TEXT", 175]
        dFieldInfo["COKEY"] = ["TEXT", 30]
        dFieldInfo["COMPNAME"] = ["TEXT", 60]
        dFieldInfo["CHKEY"] = ["TEXT", 30]
        dFieldInfo["COMPPCT_R"] = ["SHORT", ""]
        dFieldInfo["HZDEPT_R"] = ["SHORT", ""]
        dFieldInfo["HZDEPB_R"] = ["SHORT", ""]
        #dFieldInfo["INTERPHR"] = ["DOUBLE", ""]
        dFieldInfo["INTERPHR"] = ["FLOAT", ""]  # trying to match muaggatt data type

        if dSDV["attributetype"].lower() == "interpretation" and (bFuzzy == True or dSDV["effectivelogicaldatatype"].lower() == "float"):
            #dFieldInfo["INTERPHRC"] = ["DOUBLE", ""]
            dFieldInfo["INTERPHRC"] = ["FLOAT", ""]

        else:
            dFieldInfo["INTERPHRC"] = ["TEXT", 254]

        dFieldInfo["MONTH"] = ["TEXT", 10]
        dFieldInfo["MONTHSEQ"] = ["SHORT", ""]
        dFieldInfo["COMONTHKEY"] = ["TEXT", 30]
        #PrintMsg(" \nSet final output column '" + resultcolumn + "' to " + str(dFieldInfo[resultcolumn]), 1)
        #PrintMsg(" \nSet initial column 'INTERPHRC' to " + str(dFieldInfo["INTERPHRC"]), 1)



        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        # There is a problem because the XML for the legend does not always match case
        # Create a dictionary as backup, but uppercase and use that to store the original values
        #
        # Assume that data types of string and vtext do not have domains
        global domainValues, domainValuesUp

        if not dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:
            domainValues = GetRatingDomain(gdb)
            #PrintMsg( "\ndomainValues: " + str(domainValues), 1)
            domainValuesUp = [x.upper() for x in domainValues]

        else:
            domainValues = list()
            domainValuesUp = list()


        # Get map legend information from the maplegendxml string
        # For some interps, there are case mismatches with the actual rating values. This
        # problem originates in the Rule Manager. This affects dLegend, legendValues, domainValues, dValues and dLabels.
        # At some point I need to use outputValues to fix these.
        #
        global dLegend
        dLegend = GetMapLegend(dSDV)    # dictionary containing all maplegendxml properties

        global dLabels
        dLabels = dict()

        if len(dLegend) > 0 :

            if not dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
                # effectivelogicaldatatype
                #PrintMsg(" \nJust got dLegend: " + str(dLegend), 1)
                legendValues = GetValuesFromLegend(dLegend)
                dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext
                PrintMsg(" \ndLabels: " + str(dLabels), 1)

                if len(domainValues) == 0:
                    if "value" in dLabels[1]:
                        for i in range(1, (len(dLabels) + 1)):
                            domainValues.append(dLabels[i]["value"])

                    else:
                        raise MyError, "Section not handled"




                else:
                    raise MyError, "No handle for this part"


            elif dSDV["attributename"] == "National Commodity Crop Productivity Index v3":
                PrintMsg(" \nThis is NCCPI section of GetMapLegend...", 1)

                # effectivelogicaldatatype
                #PrintMsg(" \nJust got dLegend: " + str(dLegend), 1)
                legendValues = GetValuesFromLegend(dLegend)
                dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext
                PrintMsg(" \ndLabels: " + str(dLabels), 1)

                #dLabels[1] =
                #{'upper_value': '0.200', 'order': '1', 'lower_value': '0.000', 'label': 'Low inherent productivity'}

                #dLabels[len(dLabels)] =
                #{'upper_value': '1.000', 'order': '5', 'lower_value': '0.800', 'label': 'High inherent productivity'}


            else :
                # No map legend information in xml. Must be Progressive or using fuzzy values instead of original classes.
                #
                # This causes a problem for NCCPI.
                PrintMsg(" \nNo map legend information for " + sdvAtt + " \n ", 1)
                #dLabels = dict()
                legendValues = list()  # empty list, no legend
                dLegend["name"] = "Progressive"  # bFuzzy
                dLegend["type"] = "1"

        else:
            # No map legend information in xml. Must be Progressive or using fuzzy values instead of original classes.
            #
            # This causes a problem for NCCPI.
            PrintMsg(" \nNo map legend information for " + sdvAtt + " \n ", 1)
            #dLabels = dict()
            legendValues = list()  # empty list, no legend
            dLegend["name"] = "Progressive"  # bFuzzy
            dLegend["type"] = "1"

        # If there are no domain values, try using the legend values instead.
        # May want to reconsider this move
        #
        if len(legendValues) > 0:
            if len(domainValues) == 0:
                domainValues = legendValues

        # Create a dictionary based upon domainValues or legendValues.
        # This dictionary will use an uppercase-string version of the original value as the key
        #
        global dValues
        dValues = dict()  # Try creating a new dictionary. Key is uppercase-string value. Value = [order, original value]

        # Some problems with the 'Not rated' data value, legend value and sdvattribute setting ("notratedphrase")
        # No perfect solution.
        #
        # Start by cleaning up the not rated value as best possible
        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False:
            if not dSDV["notratedphrase"] is None:
                # see if the lowercase value is equivalent to 'not rated'
                if dSDV["notratedphrase"].upper() == 'NOT RATED':
                    dSDV["notratedphrase"] = 'Not rated'

                else:
                    dSDV["notratedphrase"] == dSDV["notratedphrase"][0:1].upper() + dSDV["notratedphrase"][1:].lower()

            else:
                dSDV["notratedphrase"] = 'Not rated' # no way to know if this is correct until all of the data has been processed

            #
            # Next see if the not rated value exists in the domain from mdstatdomdet or map legend values
            bNotRated = False

            for d in domainValues:
                if d.upper() == dSDV["notratedphrase"].upper():
                    bNotRated = True

            if bNotRated == False:
                domainValues.insert(0, dSDV["notratedphrase"])

            if dSDV["ruledesign"] == 2:
                # Flip legend (including Not rated) for suitability interps
                domainValues.reverse()
        #
        # Populate dValues dictionary using domainValues
        #
        if len(domainValues) > 0:
            #PrintMsg(" \nIn main, domainValues looks like: " + str(domainValues), 1)

            for val in domainValues:
                #PrintMsg("\tAdding key value (" + val.upper() + ") to dValues dictionary", 1)
                dValues[str(val).upper()] = [len(dValues), val]  # new 02/03

        #PrintMsg(" \ndValues: " + str(dValues), 1)

        # For the result column we need to translate the sdvattribute value to an ArcGIS field data type
        #  'Choice' 'Float' 'Integer' 'string' 'String' 'VText'
        if dSDV["attributelogicaldatatype"].lower() in ['string', 'choice']:
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["TEXT", dSDV["attributefieldsize"]]

        elif dSDV["attributelogicaldatatype"].lower() == "vtext":
            # Not sure if 254 is adequate
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["TEXT", 254]

        elif dSDV["attributelogicaldatatype"].lower() == "integer":
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["SHORT", ""]

        elif dSDV["attributelogicaldatatype"].lower() == "float":
            dFieldInfo[dSDV["attributecolumnname"].upper()] = ["FLOAT", dSDV["attributeprecision"]]

        else:
            raise MyError, "Failed to set dFieldInfo for " + dSDV["attributecolumnname"].upper()

        # Identify related tables using mdstatrshipdet and add to tblList
        #
        mdTable = os.path.join(gdb, "mdstatrshipdet")
        mdFlds = ["LTABPHYNAME", "RTABPHYNAME", "LTABCOLPHYNAME", "RTABCOLPHYNAME"]
        level = 0  # table depth
        tblList = list()

        # Make sure mdstatrshipdet table is populated.
        if int(arcpy.GetCount_management(mdTable).getOutput(0)) == 0:
            raise MyError, "Required table (" + mdTable + ") is not populated"

        # Clear previous map layer if it exists
        # Need to change layer file location to "gdb" for final production version
        #
        if dAgg[aggMethod] != "":
            outputLayer = sdvAtt + " " + dAgg[aggMethod]

        else:
            outputLayer = sdvAtt

        if top > 0 or bot > 0:
            outputLayer = outputLayer + ", " + str(top) + " to " + str(bot) + "cm"
            tf = "HZDEPT_R"
            bf = "HZDEPB_R"

            if (bot - top) == 1:
                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

            else:
                #PrintMsg(" \nTesting horizon SQL", 1)
                rng = str(tuple(range(top, (bot + 1))))
                #hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )" # works

                hzQuery = "((" + tf + " BETWEEN " + str(top) + " AND " + str(bot) + " OR " + bf + " BETWEEN " + str(top) + " AND " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )" # test

                #hzQuery = "( " + bf  + " >= " + str(top) + " ) AND (" + tf + " <= " + str(bot) + " )"

        elif secCst != "":
            #PrintMsg(" \nAdding primary and secondary constraint to layer name (" + primCst + " " + secCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst + ", " + secCst

        elif primCst != "":
            #PrintMsg(" \nAdding primaryconstraint to layer name (" + primCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst

        if begMo != "" or endMo != "":
            outputLayer = outputLayer + ", " + str(begMo) + " - " + str(endMo)

        # Check to see if the layer already exists and delete if necessary
        layers = arcpy.mapping.ListLayers(mxd, outputLayer, df)
        if len(layers) == 1:
            arcpy.mapping.RemoveLayer(df, layers[0])

        # Create list of tables in the ArcMap TOC. Later check to see if a table
        # involved in queries needs to be removed from the TOC.
        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)
        mainTables = ['mapunit', 'component', 'chorizon']

        for tv in tableViews:
            if tv.datasetName.lower() in mainTables:
                # Remove this table view from ArcMap that might cause a conflict with queries
                arcpy.mapping.RemoveTableView(df, tv)

        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)   # any other table views...
        rtabphyname = "XXXXX"
        mdSQL = "RTABPHYNAME = '" + dSDV["attributetablename"].lower() + "'"  # initial whereclause for mdstatrshipdet

        # Setup initial queries
        while rtabphyname != "MAPUNIT":
            level += 1

            with arcpy.da.SearchCursor(mdTable, mdFlds, where_clause=mdSQL) as cur:
                # This should only select one record

                for rec in cur:
                    ltabphyname = rec[0].upper()
                    rtabphyname = rec[1].upper()
                    ltabcolphyname = rec[2].upper()
                    rtabcolphyname = rec[3].upper()
                    mdSQL = "RTABPHYNAME = '" + ltabphyname.lower() + "'"
                    if bVerbose:
                        PrintMsg("\tGetting level " + str(level) + " information for " + rtabphyname.upper(), 1)

                    tblList.append(rtabphyname) # save list of tables involved

                    for tv in tableViews:
                        if tv.datasetName.lower() == rtabphyname.lower():
                            # Remove this table view from ArcMap that might cause a conflict with queries
                            arcpy.mapping.RemoveTableView(df, tv)

                    if rtabphyname.upper() == dSDV["attributetablename"].upper():
                        #
                        # This is the table that contains the rating values
                        #
                        # check for primary and secondary restraints
                        # and use a query to apply them if found.

                        # Begin setting up SQL statement for initial filter
                        # This may be changed further down
                        #
                        if dSDV["attributelogicaldatatype"].lower() in ['integer', 'float']:
                            # try to eliminate calculation failures on NULl values
                            try:
                                primSQL = dSDV["attributecolumnname"].upper() + " is not null and " + dSDV["sqlwhereclause"] # sql applied to bottom level table

                            except:
                                primSQL = dSDV["attributecolumnname"].upper() + " is not null"

                        else:
                            try:
                                primSQL = dSDV["sqlwhereclause"]

                            except:
                                primSQL = None

                        if not primaryconcolname is None:
                            # has primary constraint, get primary constraint value
                            if primSQL is None:
                                primSQL = primaryconcolname + " = '" + primCst + "'"

                            else:
                                primSQL = primSQL + " and " + primaryconcolname + " = '" + primCst + "'"

                            if not secondaryconcolname is None:
                                # has primary constraint, get primary constraint value
                                secSQL = secondaryconcolname + " = '" + secCst + "'"
                                primSQL = primSQL + " and " + secSQL
                                #PrintMsg(" \nprimSQL = " + primSQL, 0)

                        if dSDV["attributetablename"].upper() == "COINTERP":

                            #interpSQL = "MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"
                            interpSQL = "RULEDEPTH = 0 AND MRULENAME = '" + dSDV["nasisrulename"] + "'"

                            if primSQL is None:
                                primSQL = interpSQL
                                #primSQL = "MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"

                            else:
                                #primSQL = primSQL + " and MRULENAME like '%" + dSDV["nasisrulename"] + "' and RULEDEPTH = 0"
                                primSQL = interpSQL + " AND " + primSQL

                            # Try populating the cokeyList variable here and use it later in ReadTable
                            cokeyList = list()

                        elif dSDV["attributetablename"].upper() == "CHORIZON":
                            if primSQL is None:
                                primSQL = hzQuery

                            else:
                                primSQL = primSQL + " and " + hzQuery

                        elif dSDV["attributetablename"].upper() == "CHUNIFIED":
                            if primSQL is None:
                                primSQL = primSQL + " and RVINDICATOR = 'Yes'"

                            else:
                                primSQL = "CHUNIFIED.RVINDICATOR = 'Yes'"

                        elif dSDV["attributetablename"].upper() == "COMONTH":
                            if primSQL is None:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = "(MONTHSEQ = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = "(MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            else:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = primSQL + " AND (MONTHSEQ = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = primSQL + " AND (MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                        elif dSDV["attributetablename"].upper() == "COSOILMOIST":
                            # Having problems with NULL values for some months. Need to retain NULL values with query,
                            # but then substitute 201cm in ReadTable
                            #
                            primSQL = dSDV["sqlwhereclause"]


                        if primSQL is None:
                            primSQL = ""

                        if bVerbose:
                            PrintMsg("\tRating table (" + rtabphyname.upper() + ") SQL: " + primSQL, 1)

                        # Create list of necessary fields

                        # Get field list for mapunit or component or chorizon
                        if rtabphyname in big3Tbls:
                            flds = dFields[rtabphyname]
                            if not dSDV["attributecolumnname"].upper() in flds:
                                flds.append(dSDV["attributecolumnname"].upper())

                            dFields[rtabphyname] = flds
                            dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)

                        else:
                            # Not one of the big 3 tables, just use foreign key and sdvattribute column
                            flds = [rtabcolphyname, dSDV["attributecolumnname"].upper()]
                            dFields[rtabphyname] = flds

                            if not rtabphyname in dMissing:
                                dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)
                                #PrintMsg("\nSetting missing fields for " + rtabphyname + " to " + str(dMissing[rtabphyname]), 1)

                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # For tables other than the primary ones.
                            sql = (None, None)

                        if rtabphyname == "MAPUNIT" and aggMethod != "No Aggregation Necessary":
                            # No aggregation necessary?
                            dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dMapunit) == 0:
                                raise MyError, "No data for " + sdvAtt

                        elif rtabphyname == "COMPONENT":
                            #if cutOff is not None:
                            if dSDV["sqlwhereclause"] is not None:
                                if cutOff == 0:
                                    # Having problems with CONUS database. Including COMPPCT_R in the
                                    # where_clause is returning zero records. Found while testing Hydric map. Is a Bug?
                                    # Work around is to put COMPPCT_R part of query last in the string

                                    primSQL =  dSDV["sqlwhereclause"]

                                else:
                                    primSQL = dSDV["sqlwhereclause"] + ' AND "COMPPCT_R" >= ' + str(cutOff)

                            else:
                                primSQL = "COMPPCT_R >= " + str(cutOff)


                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dComponent) == 0:
                                raise MyError, "No data for " + sdvAtt

                        elif rtabphyname == "CHORIZON":
                            #primSQL = "(CHORIZON.HZDEPT_R between " + str(top) + " and " + str(bot) + " or CHORIZON.HZDEPB_R between " + str(top) + " and " + str(bot + 1) + ")"
                            #PrintMsg(" \nhzQuery: " + hzQuery, 1)
                            dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)

                            if len(dHorizon) == 0:
                                raise MyError, "No data for " + sdvAtt

                        else:
                            # This should be the bottom-level table containing the requested data
                            #
                            cokeyList = list()  # Try using this to pare down the COINTERP table record count
                            #cokeyList = dComponent.keys()  # Won't work. dComponent isn't populated yet

                            dTbl = ReadTable(dSDV["attributetablename"].upper(), flds, primSQL, level, sql)

                            if len(dTbl) == 0:
                                raise MyError, " \nNo data for " + sdvAtt

                    else:
                        # Bottom section
                        #
                        # This is one of the intermediate tables
                        # Create list of necessary fields
                        # Get field list for mapunit or component or chorizon
                        #
                        flds = dFields[rtabphyname]
                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # This needs to be fixed. I have a whereclause in the try and an sqlclause in the except.
                            sql = (None, None)

                        primSQL = ""
                        #PrintMsg(" \n\tReading intermediate table: " + rtabphyname + "   sql: " + str(sql), 1)

                        if rtabphyname == "MAPUNIT":
                            dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "COMPONENT":
                            primSQL = "COMPPCT_R >= " + str(cutOff)

                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "CHORIZON":
                            #primSQL = "(CHORIZON.HZDEPT_R between " + str(top) + " and " + str(bot) + " or CHORIZON.HZDEPB_R between " + str(top) + " and " + str(bot + 1) + ")"
                            tf = "HZDEPT_R"
                            bf = "HZDEPB_R"
                            #primSQL = "( ( " + tf + " between " + str(top) + " and " + str(bot - 1) + " or " + bf + " between " + str(top) + " and " + str(bot) + " ) or " + \
                            #"( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"
                            if (bot - top) == 1:
                                #rng = str(tuple(range(top, (bot + 1))))
                                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            else:
                                rng = str(tuple(range(top, bot)))
                                hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            #PrintMsg(" \nSetting primSQL for when rtabphyname = 'CHORIZON' to: " + hzQuery, 1)
                            dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)

                        elif rtabphyname == "COMONTH":

                            # Need to look at the SQL for the other tables as well...
                            if begMo == endMo:
                                # query for single month
                                primSQL = "(MONTHSEQ = " + str(moList.index(begMo)) + ")"

                            else:
                                primSQL = "(MONTHSEQ IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            #PrintMsg(" \nIntermediate SQL: " + primSQL, 1)
                            dMonth = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            if len(dMonth) == 0:
                                raise MyError, "No data for " + sdvAtt + " \n "
                            #else:
                            #    PrintMsg(" \nFound " + str(len(dMonth)) + " records in COMONTH", 1)

                        else:
                            PrintMsg(" \n\tUnable to read data from: " + rtabphyname, 1)


            if level > 6:
                raise MyError, "Failed to get table relationships"


        # Create a list of all fields needed for the initial output table. This
        # one will include primary keys that won't be in the final output table.
        #
        if len(tblList) == 0:
            # No Aggregation Necessary, append field to mapunit list
            tblList = ["MAPUNIT"]
            if dSDV["attributecolumnname"].upper() in dFields["MAPUNIT"]:
                PrintMsg(" \nSkipping addition of field "  + dSDV["attributecolumnname"].upper(), 1)

            else:
                dFields["MAPUNIT"].append(dSDV["attributecolumnname"].upper())

        tblList.reverse()  # Set order of the tables so that mapunit is on top

        if bVerbose:
            PrintMsg(" \nUsing these tables: " + ", ".join(tblList), 1)

        # Create a list of all fields to be used
        global allFields
        allFields = ["AREASYMBOL"]
        allFields.extend(dFields["MAPUNIT"])  # always include the selected set of fields from mapunit table
        #PrintMsg(" \nallFields 1: " + ", ".join(allFields), 1)

        # Substitute resultcolumname for last field in allFields
        for tbl in tblList:
            tFields = dFields[tbl]
            for fld in tFields:
                if not fld.upper() in allFields:
                    #PrintMsg("\tAdding " + tbl + "." + fld.upper(), 1)
                    allFields.append(fld.upper())

        if not dSDV["attributecolumnname"].upper() in allFields:
            allFields.append(dSDV["attributecolumnname"].upper())

        #PrintMsg(" \nallFields 3: " + ", ".join(allFields), 1)

        # Create initial output table (one-to-many)
        # Now created with resultcolumnname
        #
        initialTbl = CreateInitialTable(gdb, allFields, dFieldInfo)

        if initialTbl is None:
            raise MyError, "Failed to create initial query table"

        # Create dictionary for areasymbol
        #PrintMsg(" \nGetting polygon count...", 1)
        global polyCnt, fcCnt
        polyCnt = int(arcpy.GetCount_management(inputLayer).getOutput(0))  # featurelayer polygon count
        fcCnt = int(arcpy.GetCount_management(fc).getOutput(0))            # featureclass polygon count
        #PrintMsg(" \nGot polygon count of " + Number_Format(polyCnt, 0, True), 1)

        # Getting Areasymbols and legendkeys is a bottleneck (Thursday Aug 18). Any room for improvement?
        #
        #PrintMsg(" \nGetting areasymbols...", 1)
        global dAreasymbols
        dAreasymbols = GetAreasymbols(gdb)

        if len(dAreasymbols) == 0:
            raise MyError, ""

        # Made changes in the table relates code that creates tblList. List now has MAPUNIT in first position
        #

        if tblList == ['MAPUNIT']:
            # No aggregation needed
            if CreateRatingTable1(tblList, dSDV["attributetablename"].upper(), initialTbl, dAreasymbols) == False:
                raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT']:
            if CreateRatingTable2(tblList, dSDV["attributetablename"].upper(), dComponent, initialTbl) == False:
                raise MyError, ""
            del dComponent

        elif tblList == ['MAPUNIT', 'COMPONENT', 'CHORIZON']:
            if CreateRatingTable3(tblList, dSDV["attributetablename"].upper(), dComponent, dHorizon, initialTbl) == False:
                raise MyError, ""
            del dComponent, dHorizon

        elif tblList == ['MAPUNIT', 'COMPONENT', 'CHORIZON', dSDV["attributetablename"].upper()]:
            # COMPONENT, CHORIZON, CHTEXTUREGRP
            if CreateRatingTable3S(tblList, dSDV["attributetablename"].upper(), dComponent, dHorizon, dTbl, initialTbl) == False:
                raise MyError, ""
            del dComponent, dHorizon

        elif tblList in [['MAPUNIT', "MUAGGATT"], ['MAPUNIT', "MUCROPYLD"]]:
            if CreateRatingTable1S(tblList, dSDV["attributetablename"].upper(), dTbl, initialTbl, dAreasymbols) == False:
                raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT', dSDV["attributetablename"].upper()]:
            if dSDV["attributetablename"].upper() == "COINTERP":
                if CreateRatingInterps(tblList, dSDV["attributetablename"].upper(), dComponent, dTbl, initialTbl) == False:
                    raise MyError, ""
                del dComponent

            else:
                if CreateRatingTable2S(tblList, dSDV["attributetablename"].upper(), dComponent, dTbl, initialTbl) == False:
                    raise MyError, ""

        elif tblList == ['MAPUNIT', 'COMPONENT', 'COMONTH', 'COSOILMOIST']:
            if dSDV["attributetablename"].upper() == "COSOILMOIST":

                #PrintMsg(" \ndMissing values before CreateSoilMoistureTable: " + str(dMissing))

                if CreateSoilMoistureTable(tblList, dSDV["attributetablename"].upper(), dComponent, dMonth, dTbl, initialTbl, begMo, endMo) == False:
                    raise MyError, ""
                del dMonth, dComponent # trying to lower memory usage

            else:
                PrintMsg(" \nCannot handle table:" + dSDV["attributetablename"].upper(), 1)
                raise MyError, "Tables Bad Combo: " + str(tblList)

        else:
            # Need to add ['COMPONENT', 'COMONTH', 'COSOILMOIST']
            raise MyError, "Problem with list of input tables: " + str(tblList)

        # **************************************************************************
        # Look at attribflags and apply the appropriate aggregation function

        if not arcpy.Exists(initialTbl):
            # Output table was not created. Exit program.
            raise MyError, ""

        #PrintMsg(" \ninitialTbl has " + arcpy.GetCount_management(initialTbl).getOutput(0) + " records", 1)

        if int(arcpy.GetCount_management(initialTbl).getOutput(0)) == 0:
            #
            raise MyError, "Failed to populate query table"

        # Proceed with aggregation if the intermediate table has data.
        # Add result column to fields list
        iFlds = len(allFields)
        newField = dSDV["resultcolumnname"].upper()

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)
        allFields[len(allFields) - 1] = newField
        rmFields = ["MUSYM", "COMPNAME", "LKEY"]
        for fld in rmFields:
            if fld in allFields:
                allFields.remove(fld)

        if newField == "MUNAME":
            allFields.remove("MUNAME")

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)

        # Create name for final output table that will be saved to the input gSSURGO database
        #
        global tblName

        if dAgg[aggMethod] == "":
            # No aggregation method necessary
            tblName = "SDV_" + dSDV["resultcolumnname"]

        else:
            if secCst != "":
                tblName = "SDV_" + dSDV["resultcolumnname"]  + "_" + primCst.replace(" ", "_") + "_" + secCst.replace(" ", "_")

            elif primCst != "":
                tblName = "SDV_" + dSDV["resultcolumnname"] + "_" + primCst.replace(" ", "_")

            elif top > 0 or bot > 0:
                tblName = "SDV_" + dSDV["resultcolumnname"] + "_" + str(top) + "to" + str(bot)

            else:
                tblName = "SDV_" + dSDV["resultcolumnname"]

        # **************************************************************************
        #
        # Aggregation Logic to determine which functions will be used to process the
        # intermediate table and produce the final output table.
        #
        # This is where outputValues is set
        #
        if dSDV["attributetype"] == "Property":
            # These are all Soil Properties

            if dSDV["mapunitlevelattribflag"] == 1:
                # This is a Map unit Level Soil Property
                #PrintMsg("Map unit level, no aggregation neccessary", 1)
                outputTbl, outputValues = Aggregate1(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

            elif dSDV["complevelattribflag"] == 1:

                if dSDV["horzlevelattribflag"] == 0:
                    # These are Component Level-Only Soil Properties

                    if dSDV["cmonthlevelattribflag"] == 0:
                        #
                        #  These are Component Level Soil Properties

                        if aggMethod == "Dominant Component":
                            #PrintMsg(" \n1. domainValues: " + ", ".join(domainValues), 1)
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Minimum or Maximum":
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Dominant Condition":
                            if bVerbose:
                                PrintMsg(" \nDomain Values are now: " + str(domainValues), 1)

                            if len(domainValues) > 0 and dSDV["tiebreakdomainname"] is not None :
                                if bVerbose:
                                    PrintMsg(" \n1. aggMethod = " + aggMethod + " and domainValues = " + str(domainValues), 1)
                                outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #PrintMsg(" \nOuputValues: " + str(outputValues), 1)

                            else:
                                if bVerbose:
                                    PrintMsg(" \n2. aggMethod = " + aggMethod + " and no domainValues", 1)

                                outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Minimum or Maximum":
                            #
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Weighted Average" and dSDV["attributetype"].lower() == "property":
                            # Using NCCPI for any numeric component level value?
                            # This doesn't seem to be working for Range Prod 2016-01-28
                            #
                            outputTbl, outputValues = AggregateCo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)

                        elif aggMethod == "Weighted Average" and SDV["attributetype"].lower() == "intepretation":
                            # Using NCCPI for any numeric component level value?
                            # This doesn't seem to be working for Range Prod 2016-01-28
                            #
                            PrintMsg(" \nShould not hit this code using Aggregate2_NCCPI function", 1)
                            outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif aggMethod == "Percent Present":
                            # This is Hydric?
                            outputTbl, outputValues = AggregateCo_PP_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            # Don't know what kind of interp this is
                            raise MyError, "5. Component aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


                    elif dSDV["cmonthlevelattribflag"] == 1:
                        #
                        # These are Component-Month Level Soil Properties
                        #
                        if dSDV["resultcolumnname"].startswith("Dep2WatTbl"):
                            #PrintMsg(" \nThis is Depth to Water Table (" + dSDV["resultcolumnname"] + ")", 1)

                            if aggMethod == "Dominant Component":
                                outputTbl, outputValues = AggregateCo_DCP_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Dominant Condition":
                                outputTbl, outputValues = AggregateCo_Mo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #raise MyError, "EARLY OUT"

                            elif aggMethod == "Weighted Average":
                                outputTbl, outputValues = AggregateCo_WTA_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                # Component-Month such as depth to water table - Minimum or Maximum
                                outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)
                                #raise MyError, "5. Component-comonth aggregation method has not yet been developed "

                        else:
                            # This will be flooding or ponding frequency. In theory these should be the same value
                            # for each month because these are normally annual ratings
                            #
                            # PrintMsg(" \nThis is Flooding or Ponding (" + dSDV["resultcolumnname"] + ")", 1 )
                            #
                            if aggMethod == "Dominant Component":
                                # Problem with this aggregation method (AggregateCo_DCP). The CompPct sum is 12X because of the months.
                                outputTbl, outputValues = AggregateCo_Mo_DCP_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Dominant Condition":
                                # Problem with this aggregation method (AggregateCo_DCP_Domain). The CompPct sum is 12X because of the months.
                                outputTbl, outputValues = AggregateCo_Mo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl) # Orig
                                #PrintMsg(" \noutputValues: " + ", ".join(outputValues), 1)

                            elif aggMethod == "Minimum or Maximum":
                                outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif aggMethod == "Weighted Average":
                              outputTbl, outputValues = AggregateCo_Mo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                raise MyError, "Aggregation method: " + aggMethod + "; attibute " + dSDV["attributecolumnname"].upper()

                    else:
                        raise MyError, "Attribute level flag problem"

                elif dSDV["horzlevelattribflag"] == 1:
                    # These are all Horizon Level Soil Properties

                    if aggMethod == "Weighted Average":
                        # component aggregation is weighted average

                        if dSDV["attributelogicaldatatype"].lower() in ["integer", "float"]:
                            # Just making sure that these are numeric values, not indexes
                            if dSDV["horzaggmeth"] == "Weighted Average":
                                # Use weighted average for horizon data (works for AWC)
                                outputTbl, outputValues = AggregateHz_WTA_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            elif dSDV["horzaggmeth"] == "Weighted Sum":
                                # Calculate sum for horizon data (egs. AWS)
                                outputTbl, outputValues = AggregateHz_WTA_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "12. Weighted Average not appropriate for " + dataType

                    elif aggMethod == "Dominant Component":
                        # Need to find or build this function

                        if sdvAtt.startswith("Surface") or sdvAtt.endswith("(Surface)"):
                            #
                            # I just added this on Monday to fix problem with Surface Texture DCP
                            # Need to test
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["effectivelogicaldatatype"].lower() == "choice":
                            # Indexed value such as kFactor, cannot use weighted average
                            # for horizon properties
                            #outputTbl, outputValues = AggregateCo_DCP_Domain(gdb, sdvAtt,dSDV["attributecolumnname"].upper(), aggMethod, initialTbl)
                            outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt,dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["horzaggmeth"] == "Weighted Average":
                            #PrintMsg(" \nHorizon aggregation method = WTA and attributelogical datatype = " + dSDV["attributelogicaldatatype"].lower(), 1)
                            outputTbl, outputValues = AggregateHz_DCP_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "9. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

                    elif aggMethod == "Dominant Condition":

                        if sdvAtt.startswith("Surface") or sdvAtt.endswith("(Surface)"):
                            if dSDV["effectivelogicaldatatype"].lower() == "choice":
                                if bVerbose:
                                    PrintMsg(" \nDominant condition for surface-level attribute", 1)
                                outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                            else:
                                outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)


                        elif dSDV["effectivelogicaldatatype"].lower() in ("float", "integer"):
                            # Dominant condition for a horizon level numeric value is probably not a good idea
                            outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        elif dSDV["effectivelogicaldatatype"].lower() == "choice" and dSDV["tiebreakdomainname"] is not None:
                            # KFactor (Indexed values)
                            #if bVerbose:
                            #PrintMsg(" \nDominant condition for choice type", 1)
                            outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                        else:
                            raise MyError, "No aggregation calculation selected for DCD"

                    elif aggMethod == "Minimum or Maximum":
                        # Need to figure out aggregation method for horizon level  max-min
                        if dSDV["effectivelogicaldatatype"].lower() == "choice":
                            outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].upper(),  initialTbl)

                        else:  # These should be numeric, probably need to test here.
                            outputTbl, outputValues = AggregateHz_MaxMin_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                    else:
                        raise MyError, "'" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

                else:
                    raise MyError, "Horizon-level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

            else:
                # Should never hit this
                raise MyError, "Unknown depth level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

        elif dSDV["attributetype"].lower() == "interpretation":

            #PrintMsg(" \nDo I need to populate interp rating class values here, before aggregation?", 1)
            #PrintMsg(" \ndomainValues:" + str(domainValues), 1)

            if len(domainValues) == 0 and "label" in dLegend:
                # create fake domain using map legend labels and hope they are correct
                labelValues = dLegend["labels"]

                for i in range(1, (len(labelValues) + 1)):
                    domainValues.append(labelValues[i])


            if not 'Not rated' in domainValues and len(domainValues) > 0:
                # These are all Soil Interpretations
                domainValues.insert(0, "Not rated")


            if dSDV["ruledesign"] == 1:
                #
                # This is a Soil Interpretation for Limitations or Risk

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    #PrintMsg(" \nInterpretation; aggMethod = " + aggMethod, 1)
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float':
                    # Map fuzzy values for interps
                    PrintMsg(" \nNCCPI WTA using Aggregate2_NCCPI function", 1)
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:

                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    #PrintMsg(" \nmapunitlevelattribflag: " + str(dSDV["mapunitlevelattribflag"]) + ", complevelattribflag: " + str(dSDV["complevelattribflag"]) + ", cmonthlevelattribflag: " + str(dSDV["cmonthlevelattribflag"]) + ", horzlevelattribflag: " + str(dSDV["horzlevelattribflag"]) + ", effectivelogicaldatatype: " + dSDV["effectivelogicaldatatype"], 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

            elif dSDV["ruledesign"] == 2:
                # This is a Soil Interpretation for Suitability

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)  # changed this for Sand Suitability

                elif bFuzzy or (aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float'):
                    # This is NCCPI
                    #PrintMsg(" \nA Aggregate2_NCCPI", 1)
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    # Friday problem here for NCCPI
                    #PrintMsg(" \n" + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


            elif dSDV["ruledesign"] == 3:
                # This is a Soil Interpretation for Class. Only a very few interps in the nation use this.
                # Such as MO- Pasture hayland; MT-Conservation Tree Shrub Groups; CA- Revised Storie Index

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float':
                    # This is NCCPI?
                    outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    #PrintMsg(" \nNot sure about aggregation method for ruledesign = 3", 1)
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].upper(), initialTbl)

                else:
                    # Don't know what kind of interp this is
                    PrintMsg(" \nRuledesign 3: " + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Interp aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"


            elif dSDV["ruledesign"] is None:
                # This is a Soil Interpretation???
                raise MyError, "Soil Interp with no RuleDesign setting"

            else:
                raise MyError, "No aggregation calculation selected 10"

        else:
            raise MyError, "Invalid SDV AttributeType: " + str(dSDV["attributetype"])




        # quit if no data is available for selected property or interp
        if len(outputValues) == 0 or (len(outputValues) == 1 and (outputValues[0] == None or outputValues[0] == "")):
            raise MyError, "No data available for '" + sdvAtt + "'"
            #PrintMsg("No data available for '" + sdvAtt + "'", 1)

        if BadTable(outputTbl):
            raise MyError, "No data available for '" + sdvAtt + "'"

        #if not bVerbose:
            # delete sdv_initial table
            #arcpy.Delete_management(initialTbl)

        # End of New Aggregation Logic
        # **************************************************************************

    # End of parameter descriptions

        # Test JSON code for symbology
        if bVerbose:
            PrintMsg(" \noutputValues: " + str(outputValues), 1)

        if outputValues == [-999999999, 999999999]:
            raise MyError, "We have an outputValues problem"



        # Adding new code on 2017-07-27 to try and address case mismatches between data and map legend values
        # This affects dLegend, legendValues, domainValues, dValues and dLabels.

        if dSDV["effectivelogicaldatatype"] != 'float':
            # NCCPI is failing. Should I be skipping effectivelogicaldatatype == 'float'???
            arcpy.SetProgressorLabel("Getting map legend information")
            # Fix dLegend first
            dLabels = dLegend["labels"]   # NCCPI is failing here
            end = len(dLabels) + 1



            try:

                for i in range(1, end):
                    labelInfo = dLabels[i]
                    order = labelInfo["order"]
                    value = labelInfo["value"]
                    label = labelInfo["label"]

                    if value.upper() in dValues:
                        # Compare value to outputValues
                        for dataValue in outputValues:
                            if dataValue.upper() == value.upper():
                                value = dataValue
                                labelInfo["value"] = value
                                dLabels[i] = labelInfo

                dLegend["labels"] = dLabels

            except:
                pass

                # Fix domainValues
                try:

                    for dv in domainValues:
                        for dataValue in outputValues:

                            if dataValue.upper() == dv.upper() and dataValue != dv:
                                indx = domainValues.index(dv)
                                junk = domainValues.pop(indx)
                                domainValues.insert(indx, dataValue)

                except:
                    pass

                # Fix dValues
                try:
                    for key, val in dValues.items():
                        seq, dv = val

                        for dataValue in outputValues:

                            if dataValue.upper() == key and dataValue != dv:
                                indx = domainValues.index(dv)
                                junk = domainValues.pop(indx)
                                val =[seq, dataValue]
                                dValues[key] = val

                except:
                    pass

            #
            # End of case-mismatch code


        #PrintMsg(" \nLegend name in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)

        if dLegend["name"] != "Random" and muDesc.dataType.lower() == "featurelayer":
            #PrintMsg(" \nLegend name 1 in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)

            global dLayerDefinition
            dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"])

            #PrintMsg(" \nLegend name 2 in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)
            #PrintMsg(" \n" + str(dLayerDefinition), 1)

            #classBreakInfos = dLayerDefinition['drawingInfo']['renderer']['classBreakInfos']
            #
            # Note to self. Problem must be in the CreateJSONLegend function. For Hydric I am getting five
            # duplicate copies of the classBreakInfos dictionary.
            #
            #PrintMsg(" \nContents of classBreakInfos: " + str(classBreakInfos) , 1)
            #for cb in classBreakInfos:
            #    PrintMsg(" \n" + str(cb), 1)
            #PrintMsg(" \ndLayerDefinition in CreateSoilMap: " + str(dLayerDefinition), 1)

        else:
            # Create empty legend dictionary so that CreateMapLayer function will run for Random Color legend
            dLayerDefinition = dict()

        # Create map layer with join using arcpy.mapping
        # sdvAtt, aggMethod, inputLayer
        if arcpy.Exists(outputTbl):
            global tblDesc
            tblDesc = arcpy.Describe(outputTbl)

            #PrintMsg(" \nCreating layer file for " + outputLayer + "....", 0)
            outputLayerFile = os.path.join(os.path.dirname(gdb), os.path.basename(outputLayer.replace(", ", "_").replace(" ", "_")) + ".lyr")

            # Save parameter settings for layer description
            if not dSDV["attributeuom"] is None:
                parameterString = "Units of Measure: " +  dSDV["attributeuom"]
                parameterString = parameterString + "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

            else:
                parameterString = "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

            if primCst != "":
                parameterString = parameterString + "\r\n" + dSDV["primaryconstraintlabel"] + ": " + primCst

            if secCst != "":
                parameterString = parameterString + "; " + dSDV["secondaryconstraintlabel"] + ": " + secCst

            if dSDV["horzlevelattribflag"]:
                parameterString = parameterString + "\r\nTop horizon depth: " + str(top)
                parameterString = parameterString + ";  " + "Bottom horizon depth: " + str(bot)

            elif dSDV["cmonthlevelattribflag"]:
                parameterString = parameterString + "\r\nMonths: " + begMo + " through " + endMo

            if cutOff is not None:
                parameterString = parameterString + "\r\nComponent Percent Cutoff:  " + str(cutOff) + "%"

            if dSDV["effectivelogicaldatatype"].lower() in ["float", "integer"]:
                parameterString = parameterString + "\r\nUsing " + sRV.lower() + " values (" + dSDV["attributecolumnname"] + ") from " + dSDV["attributetablename"].lower() + " table"

            # Finish adding system information to description
            #
            #
            envUser = arcpy.GetSystemEnvironment("USERNAME")
            if "." in envUser:
                user = envUser.split(".")
                userName = " ".join(user).title()

            elif " " in envUser:
                user = envUser.split(" ")
                userName = " ".join(user).title()

            else:
                userName = envUser

            parameterString = parameterString + "\r\nGeoDatabase: " + os.path.dirname(fc) + "\r\n" + muDesc.dataType.title() + ": " + \
            os.path.basename(fc) + "\r\nRating Table: " + os.path.basename(outputTbl) + \
            "\r\nLayer File: " + outputLayerFile + \
            "\r\nCreated by " + userName + " on " + datetime.date.today().isoformat() + " using script " + os.path.basename(sys.argv[0])

            if arcpy.Exists(outputLayerFile):
                arcpy.Delete_management(outputLayerFile)

            # Create metadata for outputTbl
            bMetadata = UpdateMetadata(gdb, outputTbl, parameterString)

            if bMetadata == False:
                PrintMsg(" \nFailed to update layer and table metadata", 1)

            if muDesc.dataType.lower() == "featurelayer":
                bMapLayer = CreateMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, dLayerDefinition)
                #PrintMsg(" \nFinished '" + sdvAtt + "' (" + aggMethod.lower() + ") for " + os.path.basename(gdb) + " \n ", 0)



            elif muDesc.dataType.lower() == "rasterlayer":
                bMapLayer = CreateRasterMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString)

            del mxd
            return True

        else:
            raise MyError, "Failed to create summary table and map layer \n "
            return False


    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time, operator, json
import xml.etree.cElementTree as ET
import random

# Create the environment
from arcpy import env

try:
    if __name__ == "__main__":
        inputLayer = arcpy.GetParameterAsText(0)      # Input mapunit polygon layer
        sdvFolder = arcpy.GetParameter(1)             # SDV Folder
        sdvAtt = arcpy.GetParameter(2)                # SDV Attribute
        aggMethod = arcpy.GetParameter(3)             # Aggregation method
        primCst = arcpy.GetParameter(4)               # Primary Constraint choice list
        secCst = arcpy.GetParameter(5)                # Secondary Constraint choice list
        top = arcpy.GetParameter(6)                   # top horizon depth
        bot = arcpy.GetParameter(7)                   # bottom horizon depth
        begMo = arcpy.GetParameter(8)                 # beginning month
        endMo = arcpy.GetParameter(9)                 # ending month
        tieBreaker = arcpy.GetParameter(10)           # tie-breaker setting
        bZero = arcpy.GetParameter(11)                # treat null values as zero
        cutOff = arcpy.GetParameter(12)               # minimum component percent cutoff (integer)
        bFuzzy = arcpy.GetParameter(13)               # Map fuzzy values for interps
        bNulls = arcpy.GetParameter(14)               # Include NULL values in rating summary or weighting
        sRV = arcpy.GetParameter(15)                  # flag to switch from standard RV attributes to low or high

        #global bVerbose
        #bVerbose = False   # hard-coded boolean to print diagnostic messages

        bSoilMap = CreateSoilMap(inputLayer, sdvFolder, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV)


except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
