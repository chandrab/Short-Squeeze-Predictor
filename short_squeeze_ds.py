import datetime
import ss_ds_node as ssnode
import matplotlib.pyplot as plt
from matplotlib import style
#from matplotlib.finance import candlestick_ohlc
import matplotlib.dates as mdates
import pandas as pd
import pandas_datareader.data as web
from yahoo_finance import Share
import time

# ^ all of the imports to use yahoo finance api

import operator
import bs4

from urllib.request import urlopen as uReq
from bs4 import BeautifulSoup as soup

# ^ all of the imports for BeautifulSoup



class Hash:
    """ Creates a hash table utilizing quadratic probing. """

    def __init__(self, size=7949):

        self.capacity = size
        self.num_items = 0
        self.hash_table = [None] * self.capacity
        self.primes_list = []
        self.watchlist = []
        self.get_primes('primes_to_200000.txt')
        self.neg_vol_trend_list = []
        self.pos_vol_trend_list = []
        self.neg_price_trend_list = []
        self.pos_price_trend_list = []
        self.removed_list = []
        self.low_short_shares = []
        self.high_short_shares = []
        self.high_beta_lst = []
        self.low_beta_lst = []
        self.high_shares_perc_change = []
        self.ranked_shares = {}
        self.sorted_ranked_shares = None
        self.write_list = []
        self.good_yearly_low = []
        self.bad_yearly_low = []

    def get_primes(self, filename):             # works
        """ Reads from file containing list of primes up to 200000 and appends each prime to a list. """

        f = open(filename)
        for word in f.read().split():
            self.primes_list.append(int(word))


    def get_load_fact(self):            # works
        return self.num_items / len(self.hash_table)

    def my_hash(self, key, num):        # works
        return (key + (num * num)) % len(self.hash_table)

    def find_capacity(self):            # works
        for val in self.primes_list:
            if self.capacity * 2 < val:
                self.capacity = val
                break


    def rehash(self):           # works
        """ Rehashes the entire hash_table. """
        # Figure out a way to set a new table to one efficiently, don't just do self.hash_table = tmp_table

        self.find_capacity()
        tmp_table = [None] * self.capacity

        for val in self.hash_table:
            if val:         # if there is a value in the slot, rehash into new slot
                key = 1
                ticker = val.get_ticker()

                for char in ticker:
                    key *= ord(char)

                num = 2
                cont = True

                while cont:
                    hash_val = self.my_hash(key, num)

                    if tmp_table[hash_val] is None:
                        self.num_items += 1
                        tmp_table[hash_val] = val
                        cont = False
                    num += 1

        self.hash_table = tmp_table


    def insert(self, ticker, name=None, prev_close=None, open_p=None, close=None):          # works
        """ The key will be the ascii value of each char multiplied by the total so far. Returns -1 if it cannot be entered. """

        nd = ssnode.Node(ticker, name, prev_close, open_p, close)
        key = 1

        for char in ticker:
            key *= ord(char)

        val = 2
        cont = True
        collisions = -1

        while cont:
            hash_val = self.my_hash(key, val)
            collisions += 1
            if collisions >= self.capacity:
                self.rehash()
                collisions = -1

            if self.hash_table[hash_val] is not None and self.hash_table[hash_val].get_ticker() == ticker:
                cont = False
            elif self.hash_table[hash_val] is None:
                self.num_items += 1
                if self.get_load_fact() >= 0.5:
                    self.rehash()
                if self.hash_table[hash_val] is None:
                    self.hash_table[hash_val] = nd
                    cont = False
                    return hash_val
            val += 1
        return -1


    def remove(self, ticker):       # works
        """ Will remove the node at the hash_value. Returns -1 if not found. """

        key = 1

        for char in ticker:
            key *= ord(char)

        val = 2
        while val < self.capacity:
            hash_val = self.my_hash(key, val)

            if self.hash_table[hash_val] and self.hash_table[hash_val].get_ticker() == ticker:
                tmp = self.hash_table[hash_val]
                self.hash_table[hash_val] = None
                return tmp
            val += 1
        return -1


    def get(self, ticker):              # works
        """ Will return the node which will allow you to access whatever you want (ticker, price, etc.). """

        key = 1
        ticker = ticker.upper()

        for char in ticker:
            key *= ord(char)

        val = 2
        while val < self.capacity:
            hash_val = self.my_hash(key, val)

            if self.hash_table[hash_val] and self.hash_table[hash_val].get_ticker() == ticker:
                return self.hash_table[hash_val]
            val += 1

        return -1


    def print_tcker(self):          # works
        for val in self.hash_table:
            if val is not None:
                print('$' + val.get_ticker())







    """ BEGINNING OF TRUE FUNCTIONS (I.E. THE SCREENING PART) """

# Currently, the 'perfect' stock has a volume and price uptrend, >= 5% shares float, beta > 1% or < -1, price at or below $10.00,
# and daily percent change between the days is >= 5%.





    def init_run(self):
        """ Screens the stocks and adds to watchlist if their daily percent change is >= 5. """

        not_lst = []

        self.write_list.append('Ticker\t% Chng\n\n')

        for nd in self.hash_table:
            if nd is not None:
                cont = True
                ticker = nd.get_ticker()
                url = 'https://finance.yahoo.com/quote/' + ticker + '?p=' + ticker

                # safeguards against a failed URL attempt
                page = self.get_page(url)

                # gets the current price
                try:
                    nd.curr_price = float(page.findAll('span')[9].text)
                except:
                    self.write_list.append(str(ticker + " - Couldn't get current price\n"))
                    not_lst.append(ticker)
                    cont = False


                if cont:
                    # checks if the stock is within 15% of 52 week low
                    self.check_yearly_low(nd, page)

                    # gets the previous close price
                    nd.prev_close = float(page.findAll('span', {'class':'Trsdu(0.3s) '})[0].text)

                    # calculates percent change and rounds to 3 decimals
                    nd.perc_change = round((((nd.curr_price / nd.prev_close) - 1) * 100), 3)

                    # gets the average volume
                    text_avg_volume = page.findAll('span', {'class':'Trsdu(0.3s) '})[5].text.replace(',', '')

                    # safeguards against any failed volume-getting attempts
                    try:
                        nd.avg_volume = float(text_avg_volume)
                    except:
                        # tries another spot the volume could be
                        try:
                            text_avg_volume = page.findAll('span', {'class':'Trsdu(0.3s) '})[4].text
                            text_avg_volume = text_avg_volume.replace(',', '')
                            nd.avg_volume = float(text_avg_volume)
                        except:
                            # tries another spot the volume could be
                            try:
                                text_avg_volume = page.findAll('span', {'class':'Trsdu(0.3s) '})[3].text
                                text_avg_volume = text_avg_volume.replace(',', '')
                                nd.avg_volume = float(text_avg_volume)
                            except:
                                # will not be added to watchlist
                                self.write_list.append(str(ticker + " - Couldn't get average volume\n"))
                                not_lst.append(ticker)
                                cont = False

                    # appends to the watchlist if it fits criteria
                    if cont and nd.perc_change >= 5:
                        nd.days_twenty_perc_above_avg_volume += 1
                        self.write_list.append(str(ticker + '\t' + str(nd.perc_change) + '\n'))
                        self.watchlist.append(nd)

        # prints the tickers not found, if any
        if not_lst:
            word = ''
            for i, val in enumerate(not_lst):
                if i != 0:
                    word = word + ', ' + val
                else:
                    word = val
            self.write_list.append(str('\nTickers that were not found: ' + word + '\n'))





    def check_watchlist(self):
        """ Further screens the watchlist. Calls functions that call other functions. """

        for nd in self.watchlist:
            ticker = nd.get_ticker()

            url = 'https://finance.yahoo.com/quote/' + ticker + '/history?p=' + ticker

            # safeguards against a failed URL attempt
            page = self.get_page(url)

            self.check_volume_trend(nd, page)
            self.check_price_trend(nd, page)
            self.check_shorts_beta(nd)
            self.check_pain(nd)


        append_dict = {}

        # simply sorts the stocks into postive trends and not postive trends
        self.write_list.append('\n\n\nStocks with Positive Price and Volume Trend:\n')
        for nd in self.pos_vol_trend_list:
            if nd.price_uptrend:
                self.write_list.append(nd.get_ticker() + '\n')


        append_dict = {}
        self.write_list.append('\n\n\nShares with Shorts >= 15%:\n')
        for nd in self.high_short_shares:
            if nd.shorts_percent_float >= 15:
                append_dict[nd.get_ticker()] = nd.perc_change
        append_dict = sorted(append_dict.items(), key=operator.itemgetter(1), reverse=True)
        for val in append_dict:
            self.write_list.append(str(str(val[0])+ '\t' + str(val[1]) + '\n'))


        append_dict = {}
        self.write_list.append('\n\n\nPossible Great Stocks (Short Pain, Within 15% of 52 Week Low):\n')
        for nd in self.watchlist:
            nd_trues = 0
            if nd.high_beta:
                nd_trues += 1
            if nd.high_shorts:
                nd_trues += 1
            if nd.vol_uptrend:
                nd_trues += 1
            if nd.price_uptrend:
                nd_trues += 1

            if nd_trues >= 3:
                append_dict[nd] = nd.shorts_pain
        append_dict = sorted(append_dict.items(), key=operator.itemgetter(1), reverse=True)
        for val in append_dict:
            self.write_list.append(str(str(val[0].get_ticker()) + '\t' + str(val[1]) + '\t\t' + str(val[0].yearly_low) + '\n'))


        # like I did below. If I ever want to print three or more things, just use a list for the value
        append_dict = {}
        self.write_list.append('\n\n\nThe Perfect Stocks (Positive Price, Volume Trend, High Short Shares Float. Does not Check Beta) (Short Pain, Within 15% of 52 Week Low):\n')
        for nd in self.pos_vol_trend_list:
            if nd.price_uptrend and nd in self.high_short_shares and ((nd.avg_volume * 30) >= nd.curr_volume):
                append_dict[nd] = nd.shorts_pain
        append_dict = sorted(append_dict.items(), key=operator.itemgetter(1), reverse=True)
        for val in append_dict:
            self.write_list.append(str(str(val[0].get_ticker()) + '\t' + str(val[1]) + '\t\t' + str(val[0].yearly_low) + '\n'))


        self.write_list.append('\n\nTop 10 Stocks Experiencing Greatest Pain (Short Pain, Within 15% of 52 Week Low):\n')
        if not self.sorted_ranked_shares:
            pass
        elif len(self.sorted_ranked_shares) < 10:
            for stock in self.sorted_ranked_shares:
                self.write_list.append(str(stock[0].get_ticker()) + '\t' + str(stock[1]) + '\t\t' + str(stock[0].yearly_low) + '\n')
        else:
            for stock in self.sorted_ranked_shares[:10]:
                self.write_list.append(str(stock[0].get_ticker()) + '\t' + str(stock[1]) + '\t\t' + str(stock[0].yearly_low) + '\n')

        self.write_to_file()





    def write_to_file(self):
        """ Writes all the print statements to a file automatically named by the date of next trading day. """

        next_date = self.next_open_date()

        year = next_date[0]
        month = next_date[1]
        day = next_date[2]

        filename = '../watch_lists/' + next_date[3] + '/' + month + '/watch_lists/watch_list_for_' + month + '_' + day + '_' + year + '.txt'

        with open(filename, 'w+') as f:
            for val in self.write_list:
                f.write(val)



    def check_volume_trend(self, nd, page):
        """ Checks the volume of the ticker sent in. If the volume is greater than 150% of the average volume, then the ticker
        will stay on the watchlist. Otherwise, it will be removed. """

        tr_list = page.findAll('tr')
        vol_to_beat = nd.avg_volume * 1.5

        prev_volume = 0
        vol_uptrend = 0
        vol_downtrend = 0

        # iterates through the volumes from the past 10 trading days
        trend_lst = []
        for i, tr in enumerate(reversed(tr_list[1:11])):
            try:
                volume = tr.findAll('td')[6].text
                volume = float(volume.replace(',', ''))
            except:
                break

            if volume > vol_to_beat:
                nd.days_twenty_perc_above_avg_volume += 1

            # only checks the most recent 6 days of trading for uptrend - edit this so that it is more specific and everything
            if i >= 6:
                if prev_volume < volume:
                    vol_uptrend += 1
                    vol_downtrend = 0
                    trend_lst.append(True)
                elif prev_volume > volume:
                    vol_downtrend += 1
                    trend_lst.append(False)

                # if >= two days trading with below prev_volume, everything is reset. vol_uptrend set to False
                if vol_downtrend >= 2:
                    vol_uptrend = 0
                    nd.vol_uptrend = False
                elif vol_uptrend >= 3:
                    vol_downtrend = 0
                    nd.vol_uptrend = True

                prev_volume = volume

        nd.curr_volume = float((tr_list[1].findAll('td')[6].text).replace(',', ''))

        if not nd.vol_uptrend:
            cont = True
            for t in trend_lst[4:]:
                if not t:
                    cont = False
                    break
            if cont:
                nd.vol_uptrend = True


        # removes from watchlist if it has had fewer than 2 days above 120% average volume, otherwise appends to proper list
        if nd.days_twenty_perc_above_avg_volume < 2:
                self.removed_list.append(nd)
                self.watchlist.remove(nd)
        elif nd.vol_uptrend:
            self.pos_vol_trend_list.append(nd)
        else:
            self.neg_vol_trend_list.append(nd)




    def check_price_trend(self, nd, page):
        """ Ensures the stock sent in has had a positive price trend the previous 6 trading days. If it does, it will stay on
        the watchlist, otherwise it will be removed. """

        tr_list = page.findAll('tr')
        prev_close = 0
        price_uptrend = 0
        price_downtrend = 0

        # iterates through the most recent 6 trading days
        trend_lst = []

        for i, tr in enumerate(reversed(tr_list[8:11])):

            # safeguards against any failed price gather attempts
            try:
                close = float(tr.findAll('td')[5].text)
            except:
                break

            # performs the checks for price uptrend
            if close > (prev_close * 1.025):
                price_uptrend += 1
                price_downtrend = 0
                trend_lst.append(True)
            else:
                price_downtrend += 1
                trend_lst.append(False)

            if price_downtrend >= 2:
                price_uptrend = 0
                nd.price_uptrend = False
            elif price_uptrend >= 3:
                price_downtrend = 0
                nd.price_uptrend = True

            prev_close = close

        if not nd.price_uptrend:
            cont = True
            for t in trend_lst[4:]:
                if not t:
                    cont = False
                    break
            if cont:
                nd.price_uptrend = True


        # appends node to proper list
        if nd.price_uptrend:
            self.pos_price_trend_list.append(nd)
        else:
            self.neg_price_trend_list.append(nd)





    def check_shorts_beta(self, nd):
        """ Use the statistics tab on yahoo finance and grabs lots of numbers to do calculations. Also, float means total
        shares the company made available to the public. Outstanding shares is the total amount of shares held by EVERYONE. """

        # basically, just check if the short interest (short % of float) is above 5%
        ticker = nd.get_ticker()
        cont = True

        url = 'https://finance.yahoo.com/quote/' + ticker + '/key-statistics?p=' + ticker

        page = self.get_page(url)

        i = 30
        nd.shorts_percent_float = 0

        # safeguards against a different position of the short shares percent
        while i < 52:
            try:
                if page.findAll('tr')[i].text[:16].strip() == 'Short % of Float':
                    nd.shorts_percent_float = float(page.findAll('tr')[i].text[18:].replace('%', ''))
                    break
            except:
                pass
            i += 1

        if i == 52:
            nd.days_to_cover = 'Unable to find percent float of shorts'
        else:
            nd.days_to_cover = round((nd.shorts_percent_float / nd.avg_volume), 3)

        if nd.shorts_percent_float >= 15 and nd.perc_change >= 10:
            self.high_shares_perc_change.append(nd)
        if nd.shorts_percent_float >= 5:
            self.high_short_shares.append(nd)
            nd.high = True
        elif nd.shorts_percent_float < 5:
            self.low_short_shares.append(nd)


        # checks beta here
        i = 20
        beta = 0

        # safeguards against a different position of the short shares percent
        while i < 52:
            try:
                if page.findAll('tr')[i].text[:4].strip() == 'Beta':
                    beta = float(page.findAll('tr')[i].text[5:])
                    break
            except:
                beta = 1.01
            i += 1

        if beta < 1 and beta > -1:
            self.low_beta_lst.append(nd)
        else:
            self.high_beta_lst.append(nd)
            nd.high_beta = True




    def check_yearly_low(self, nd, page):
        """ Determines if the stock is within range of the yearly low. Assigns a weight to it based on this. """

        curr = page.findAll('tr')[5].text[13:]

        low = ''
        count = 0
        for char in curr:
            count += 1
            if char == ' ':
                break
            else:
                low += char

        high = float(curr[count + 1:].replace(',', ''))
        low = float(low)

        if (nd.curr_price / (high - low)) <= 0.15:
            self.good_yearly_low.append(nd)
            nd.yearly_low = True
        else:
            self.bad_yearly_low.append(nd)

        # calculation to determine what weight to assign it




    def check_pain(self, nd):
        """ Ranks stocks that have the highest probability of a short squeeze. Salculates short percentage by percentage
            change in a day. Could also incorporate over a weekly basis, bring in other metrics, etc. Perhaps incorporate the
            amount of money the shorts have lost, too. """

        self.ranked_shares[nd] = round((nd.shorts_percent_float * nd.perc_change), 3)
        nd.shorts_pain = round((nd.shorts_percent_float * nd.perc_change), 3)
        self.sorted_ranked_shares = sorted(self.ranked_shares.items(), key=operator.itemgetter(1), reverse=True)




    def get_page(self, url):
        """ Abstraction to protect against failed URL attempts. """

        sleep_cont = 0
        cont = True

        while cont:
            try:
                client_page = uReq(url)
                webpage = client_page.read()
                cont = False
            except:
                sleep_cont += 1
                time.sleep(5)
                if sleep_cont > 5:
                    self.write_list.append('Something seems to be wrong with your connection\n')

        client_page.close()
        return(soup(webpage, 'html.parser'))



    def next_open_date(self):
        """ Returns the date, in numbers, of the next day the market is open to properly name the txt file. """

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)

        # [month, day]
        closed_dates = [(1, 1), (1, 15), (2, 19), (3, 30), (5, 28), (7, 4), (9, 3), (11, 22), (12, 25)]

        time_delta = 1

        # tomorrow.weekday() returns int from 0-6, where 0 is Monday and 6 is Sunday
        if tomorrow.weekday() == 5:
            time_delta += 2

        tomorrow = today + datetime.timedelta(days=time_delta)
        month = tomorrow.month
        day = tomorrow.day

        for date in closed_dates:
            if month == date[0] and day == date[1]:
                time_delta += 1

        tomorrow = today + datetime.timedelta(days=time_delta)

        year = str(tomorrow.year)[2:]
        month = str(tomorrow.month)
        day = str(tomorrow.day)

        # year, month, day, COMPLETE year
        ret_lst = [year, month, day, str(tomorrow.year), ]

        return(ret_lst)





    def alt_init_run(self):
        """ Will test if the stock has had another day where the stock volume was over 120% the average, returns
            True if it was added to watchlist, False otherwise. This method uses Pandas. """

        for nd in self.hash_table:
            if nd is not None:
                start = datetime.datetime(2017, 9, 1)               # you really should store this info (avg_vol) in a var or write it to a file or something idk
                ticker = nd.get_ticker()
                cont = True

                try:
                    df = web.DataReader(ticker, 'yahoo', start)        # horribly inefficient, find a better way to get stock volume
                except:
                    cont = False

                if cont:
                    summ = 0
                    count = 0
                    lst = []


                    for index, val in df.iterrows():
                        lst.append(val)
                        summ += val['Volume']
                        count += 1
                        curr_volume = val['Volume']             # make this more efficient, find a way to assign the last value outside of the for loop

                    nd.prev_close = lst[len(lst) - 2]['Close']
                    nd.curr_price = lst[len(lst) - 1]['Close']
                    perc_change = ((nd.curr_price / nd.prev_close) - 1) * 100

                    if perc_change >= 5:
                        nd.days_twenty_perc_above_avg_volume += 1
                        self.write_list.append(ticker + '\t\t' + perc_change + '\n')

                        if nd.days_twenty_perc_above_avg_volume >= 3 and ticker not in self.watchlist:
                            self.watchlist.append(nd)
